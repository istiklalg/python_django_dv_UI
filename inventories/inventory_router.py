

class InventoryRouter:

    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'inventories':
            return 'atibadb'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'inventories':
            return 'atibadb'
        return None

    def allow_migrations(self, db, app_label, model_name=None, **hints):
        if db == 'atibadb':
            return app_label == 'inventories'
        elif app_label == 'inventories':
            return False
        return None
