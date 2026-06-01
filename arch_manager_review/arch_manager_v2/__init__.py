def classFactory(iface):
    from .plugin import ArchManagerPlugin
    return ArchManagerPlugin(iface)
