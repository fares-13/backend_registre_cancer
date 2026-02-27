from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Utilisateur, 
    MedecinProfile, 
    EpidemiologisteProfile, 
    AdminSystemeProfile, 
    ArchitectProfile
)

# Inline profiles
class MedecinProfileInline(admin.StackedInline):
    model = MedecinProfile
    can_delete = False
    verbose_name_plural = "Profil Médecin"

class EpidemiologisteProfileInline(admin.StackedInline):
    model = EpidemiologisteProfile
    can_delete = False
    verbose_name_plural = "Profil Épidémiologiste"

class AdminSystemeProfileInline(admin.StackedInline):
    model = AdminSystemeProfile
    can_delete = False
    verbose_name_plural = "Profil Admin Système"

class ArchitectProfileInline(admin.StackedInline):
    model = ArchitectProfile
    can_delete = False
    verbose_name_plural = "Profil Architecte"

@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):  # Must inherit from UserAdmin
    model = Utilisateur
    list_display = ('email', 'nom', 'prenom', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('email', 'nom', 'prenom', 'n_carte_nationale')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ("Informations Personnelles", {'fields': ('nom', 'prenom', 'sexe', 'n_carte_nationale', 'telephone')}),
        ("Permissions & Rôles", {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ("Dates importantes", {'fields': ('last_login',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'password1', 'password2', 'nom', 'prenom',
                'sexe', 'n_carte_nationale', 'role', 'is_staff', 'is_active'
            ),
        }),
    )

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

# Only register the profiles if you want to access them directly outside inline
admin.site.register(MedecinProfile)
admin.site.register(EpidemiologisteProfile)
admin.site.register(AdminSystemeProfile)
admin.site.register(ArchitectProfile)