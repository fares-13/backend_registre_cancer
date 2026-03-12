from django.contrib import admin
from .models import Patient, QuestionHabitude, ReponseHabitude, AntecedentFamilial, PatientOnboardingToken

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('id_malade', 'nom', 'prenom', 'sexe', 'deces')
    search_fields = ('nom', 'prenom', 'N_carte_nationale', 'N_securite_sociale')

@admin.register(QuestionHabitude)
class QuestionHabitudeAdmin(admin.ModelAdmin):
    list_display = ('titre', 'type_reponse', 'actif', 'ordre')
    list_editable = ('actif', 'ordre')

@admin.register(ReponseHabitude)
class ReponseHabitudeAdmin(admin.ModelAdmin):
    list_display = ('patient', 'question', 'reponse')

@admin.register(AntecedentFamilial)
class AntecedentFamilialAdmin(admin.ModelAdmin):
    list_display = ('patient', 'maladie_parent', 'age_parent', 'cancer_parent')

@admin.register(PatientOnboardingToken)
class PatientOnboardingTokenAdmin(admin.ModelAdmin):
    list_display = ('patient', 'token', 'is_used', 'expires_at')
    readonly_fields = ('token',)
