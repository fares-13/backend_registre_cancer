from django.contrib import admin
from .models import (
    Utilisateur, 
    MedecinProfile, 
    EpidemiologisteProfile, 
    AdminSystemeProfile, 
    ArchitectProfile
)

class MedecinProfileInline(admin.StackedInline):
    model = MedecinProfile
    can_delete = False
    verbose_name_plural = 'Profil Médecin'

class EpidemiologisteProfileInline(admin.StackedInline):
    model = EpidemiologisteProfile
    can_delete = False
    verbose_name_plural = 'Profil Épidémiologiste'

class AdminSystemeProfileInline(admin.StackedInline):
    model = AdminSystemeProfile
    can_delete = False
    verbose_name_plural = 'Profil Admin Système'

class ArchitectProfileInline(admin.StackedInline):
    model = ArchitectProfile
    can_delete = False
    verbose_name_plural = 'Profil Architecte'

@admin.register(Utilisateur)
class UtilisateurAdmin(admin.ModelAdmin):
    list_display = ('email', 'nom', 'prenom', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('email', 'nom', 'prenom', 'n_carte_nationale')
    ordering = ('email',)
    
    def get_inlines(self, request, obj=None):
        if obj:
            if obj.role == Utilisateur.Role.MEDECIN:
                return [MedecinProfileInline]
            elif obj.role == Utilisateur.Role.EPIDEMIOLOGISTE:
                return [EpidemiologisteProfileInline]
            elif obj.role == Utilisateur.Role.ADMIN:
                return [AdminSystemeProfileInline]
            elif obj.role == Utilisateur.Role.ARCHITECT:
                return [ArchitectProfileInline]
        return []

admin.site.register(MedecinProfile)
admin.site.register(EpidemiologisteProfile)
admin.site.register(AdminSystemeProfile)
admin.site.register(ArchitectProfile)
