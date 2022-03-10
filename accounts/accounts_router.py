

class AccountsRouter:

    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'accounts':
            return 'atibadb'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'accounts':
            return 'atibadb'
        return None

    def allow_migrations(self, db, app_label, model_name=None, **hints):
        if db == 'atibadb':
            return app_label == 'accounts'
        elif app_label == 'accounts':
            return False
        return None
