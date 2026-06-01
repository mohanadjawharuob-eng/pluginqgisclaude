"""data_manager.py — all GeoPackage / layer I/O logic, separate from UI"""
import os, json, datetime, re
from qgis.core import (
    QgsProject, QgsMapLayer, QgsFeature, QgsField, QgsFields,
    QgsVectorLayer, QgsVectorFileWriter, QgsWkbTypes,
    QgsCoordinateReferenceSystem, QgsCoordinateTransformContext
)
from qgis.PyQt.QtCore import QVariant

# ── Schema definitions ────────────────────────────────────────────────────────
SCHEMAS = {
    'contexts': [
        ('context_num', QVariant.Int), ('site', QVariant.String),
        ('type', QVariant.String), ('period', QVariant.String),
        ('description', QVariant.String), ('above_ctx', QVariant.String),
        ('below_ctx', QVariant.String), ('equals_ctx', QVariant.String),
        ('notes', QVariant.String),
    ],
    'pottery': [
        ('context_num', QVariant.Int), ('form', QVariant.String),
        ('part', QVariant.String), ('count', QVariant.Int),
        ('origin', QVariant.String), ('period', QVariant.String),
        ('notes', QVariant.String),
    ],
    'artifacts': [
        ('context_num', QVariant.Int), ('type', QVariant.String),
        ('material', QVariant.String), ('description', QVariant.String),
        ('period', QVariant.String), ('notes', QVariant.String),
    ],
    'skeletons': [
        ('skeleton_num', QVariant.Int), ('context_num', QVariant.Int),
        ('grave', QVariant.String), ('site', QVariant.String),
        ('age_group', QVariant.String), ('sex', QVariant.String),
        ('form_type', QVariant.String), ('field_notes', QVariant.String),
        ('sampled', QVariant.String), ('notes', QVariant.String),
    ],
    'bone_inventory': [
        ('skeleton_num', QVariant.Int), ('region', QVariant.String),
        ('bone', QVariant.String), ('side', QVariant.String),
        ('segment', QVariant.String), ('status', QVariant.String),
        ('notes', QVariant.String),
    ],
    'artifact_details': [
        ('artifact_id', QVariant.Int), ('context_num', QVariant.Int),
        ('image_path', QVariant.String), ('detailed_description', QVariant.String),
        ('condition', QVariant.String), ('material_detail', QVariant.String),
        ('provenance', QVariant.String), ('dimensions', QVariant.String),
        ('parallels', QVariant.String), ('notes', QVariant.String),
    ],
    'drawings': [
        ('drawing_id', QVariant.Int), ('context_num', QVariant.Int),
        ('drawing_type', QVariant.String), ('file_path', QVariant.String),
        ('scale', QVariant.String), ('notes', QVariant.String),
        ('date_recorded', QVariant.String),
    ],
    'edit_history': [
        ('history_id', QVariant.Int), ('timestamp', QVariant.String),
        ('user_name', QVariant.String), ('action', QVariant.String),
        ('table_name', QVariant.String), ('record_id', QVariant.String),
        ('details', QVariant.String),
    ],
    'context_relationships': [
        ('rel_id', QVariant.Int), ('from_ctx', QVariant.Int),
        ('to_ctx', QVariant.Int), ('rel_type', QVariant.String),
        ('source', QVariant.String), ('notes', QVariant.String),
    ],
    'excavation_grids': [
        ('grid_name', QVariant.String), ('site', QVariant.String),
        ('season', QVariant.String), ('description', QVariant.String),
        ('area_m2', QVariant.Double), ('elevation_m', QVariant.Double),
        ('date_opened', QVariant.String), ('notes', QVariant.String),
    ],
}

TABLE_NAMES = list(SCHEMAS.keys())


def coerce(val, qtype):
    """Convert a value to the correct Python type for a QVariant field.

    Handles all integer variants (GeoPackage integer columns are commonly
    reported as ``LongLong``, not ``Int``) and treats blank / NULL / None as
    a genuine NULL rather than the literal text 'NULL'.
    """
    if val is None or str(val).strip() in ('', 'NULL', 'None'):
        return None
    try:
        if qtype in (QVariant.Int, QVariant.LongLong,
                     QVariant.UInt, QVariant.ULongLong):
            return int(float(str(val)))
        if qtype == QVariant.Double:
            return float(str(val))
    except (ValueError, TypeError):
        return None
    return str(val)


def vlayers():
    """Return all valid vector layers from the current QGIS project."""
    result = []
    for lyr in list(QgsProject.instance().mapLayers().values()):
        try:
            if lyr.type() == QgsMapLayer.VectorLayer:
                result.append(lyr)
        except RuntimeError:
            pass
    return result


def lyr_from_cb(combo):
    """Get a QgsVectorLayer from a QComboBox that stores layer IDs as data."""
    if combo is None: return None
    lid = combo.currentData()
    if not lid: return None
    try:
        lyr = QgsProject.instance().mapLayer(lid)
        if lyr and lyr.isValid(): return lyr
    except RuntimeError:
        pass
    return None


def schema_for(lyr):
    """Return [(field_name, field_type)] for a layer."""
    return [(f.name(), f.type()) for f in lyr.fields()]


def write_feature(lyr, vals: dict, fid=None, user="?", history_lyr=None):
    """
    Insert (fid=None) or update (fid=int) a feature.
    vals: {field_name: value}
    Returns True on success.
    """
    fields = lyr.fields()
    field_types = {f.name(): f.type() for f in fields}
    lyr.startEditing()
    if fid is not None:
        feat = lyr.getFeature(fid)
    else:
        feat = QgsFeature(fields)
    for k, v in vals.items():
        if k in field_types:
            feat.setAttribute(k, coerce(v, field_types[k]))
    if fid is None:
        ok = lyr.addFeature(feat)
    else:
        ok = lyr.updateFeature(feat)
    if ok:
        lyr.commitChanges()
        if history_lyr:
            _log(history_lyr, 'edit' if fid else 'add',
                 lyr.name(), fid or 'new', user, str(vals)[:200])
    else:
        lyr.rollBack()
    return ok


def delete_features(lyr, fids: list, user="?", history_lyr=None):
    """Delete features by fid list. Returns True on success."""
    if not fids: return True
    lyr.startEditing()
    ok = lyr.deleteFeatures(fids)
    if ok:
        lyr.commitChanges()
        if history_lyr:
            _log(history_lyr, 'delete', lyr.name(), str(fids), user, '')
    else:
        lyr.rollBack()
    return ok


def _log(hist_lyr, action, table_name, record_id, user, details):
    """Write one row to edit_history layer."""
    try:
        feat = QgsFeature(hist_lyr.fields())
        feat.setAttribute('timestamp',
                          datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        feat.setAttribute('user_name', user)
        feat.setAttribute('action', action)
        feat.setAttribute('table_name', table_name)
        feat.setAttribute('record_id', str(record_id))
        feat.setAttribute('details', str(details)[:500])
        hist_lyr.startEditing()
        hist_lyr.addFeature(feat)
        hist_lyr.commitChanges()
    except Exception:
        pass


def create_table(gpkg_path: str, table_name: str,
                 geom_type=QgsWkbTypes.NoGeometry) -> QgsVectorLayer | None:
    """Add a new table to an existing GeoPackage. Returns the layer or None."""
    schema = SCHEMAS.get(table_name)
    if not schema:
        return None
    fields = QgsFields()
    for fname, ftype in schema:
        fields.append(QgsField(fname, ftype))
    opts = QgsVectorFileWriter.SaveVectorOptions()
    opts.driverName = 'GPKG'
    opts.fileEncoding = 'UTF-8'
    opts.layerName = table_name
    opts.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
    QgsVectorFileWriter.create(
        gpkg_path, fields, geom_type,
        QgsCoordinateReferenceSystem('EPSG:4326'),
        QgsCoordinateTransformContext(), opts)
    uri = f"{gpkg_path}|layername={table_name}"
    lyr = QgsVectorLayer(uri, table_name, 'ogr')
    return lyr if lyr.isValid() else None


def create_project(gpkg_path: str, site: str) -> dict:
    """
    Create a full project GeoPackage with all tables.
    Returns {table_name: QgsVectorLayer}.
    """
    layers = {}
    for tname in TABLE_NAMES:
        geom = (QgsWkbTypes.Polygon
                if tname == 'excavation_grids' else QgsWkbTypes.NoGeometry)
        lyr = create_table(gpkg_path, tname, geom)
        if lyr:
            lyr.setName(f"{site}_{tname}")
            QgsProject.instance().addMapLayer(lyr)
            layers[tname] = lyr
    return layers


def open_gpkg(gpkg_path: str) -> list:
    """
    Load all tables from a GeoPackage into QGIS.
    Returns list of loaded QgsVectorLayer.
    """
    loaded = []
    try:
        import sqlite3
        conn = sqlite3.connect(gpkg_path)
        cur = conn.cursor()
        cur.execute("SELECT table_name FROM gpkg_contents")
        names = [r[0] for r in cur.fetchall()]
        conn.close()
    except Exception:
        names = []
    existing_uris = {lyr.dataProvider().dataSourceUri()
                     for lyr in vlayers()}
    for name in names:
        uri = f"{gpkg_path}|layername={name}"
        if uri in existing_uris:
            continue
        lyr = QgsVectorLayer(uri, name, 'ogr')
        if lyr.isValid():
            QgsProject.instance().addMapLayer(lyr)
            loaded.append(lyr)
    return loaded


def detect_sites(layers: list) -> list:
    """
    Detect site prefixes from layer names or GeoPackage filenames.
    Returns sorted list of unique site name strings.
    """
    sep = r'[\s_\-\u2014\.]+'
    pattern = re.compile(
        sep + '(' + '|'.join(TABLE_NAMES) + r')$', re.IGNORECASE)
    prefixes = set()
    gpkg_names = set()
    for lyr in layers:
        try:
            name = lyr.name()
            m = pattern.search(name)
            if m:
                prefix = name[:len(name) - len(m.group(0))].strip()
                if prefix:
                    prefixes.add(prefix)
            uri = lyr.dataProvider().dataSourceUri()
            if '.gpkg' in uri.lower():
                gp = uri.split('|')[0]
                gpkg_names.add(os.path.splitext(os.path.basename(gp))[0])
        except Exception:
            continue
    # Fallback: bare table names → use gpkg filename
    if not prefixes:
        for lyr in layers:
            try:
                if lyr.name().lower().strip() in TABLE_NAMES:
                    uri = lyr.dataProvider().dataSourceUri()
                    if '.gpkg' in uri.lower():
                        gp = uri.split('|')[0]
                        prefixes.add(
                            os.path.splitext(os.path.basename(gp))[0])
            except Exception:
                continue
    return sorted(prefixes or gpkg_names)


def find_layer(layers: list, prefix: str, suffix: str):
    """
    Find the best matching layer for a given site prefix + table suffix.
    Returns layer id or None.
    """
    sep = r'[\s_\-\u2014\.]+'
    p, s = prefix.lower(), suffix.lower()
    for lyr in layers:
        try:
            nm = lyr.name().lower()
            if re.search(re.escape(p) + sep + re.escape(s) + '$', nm):
                return lyr.id()
        except RuntimeError:
            continue
    # Fallback: suffix only (bare gpkg)
    for lyr in layers:
        try:
            if lyr.name().lower().strip() == s:
                return lyr.id()
        except RuntimeError:
            continue
    return None


def safe_int(feat, fname: str):
    """Safely read an integer attribute from a feature."""
    try:
        v = feat.attribute(fname)
        if v is not None:
            return int(v)
    except Exception:
        pass
    return None
