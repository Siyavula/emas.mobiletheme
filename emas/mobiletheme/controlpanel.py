from plone.app.registry.browser import controlpanel

from emas.mobiletheme.interfaces import IEmasMobileThemeSettings
from emas.mobiletheme import MessageFactory as _


class EmasMobileThemeSettingsForm(controlpanel.RegistryEditForm):

    schema = IEmasMobileThemeSettings
    label = _(u'Mobile theme settings')
    description = _(u'Mobile theme settings')

    def updateFields(self):
        super(EmasMobileThemeSettingsForm, self).updateFields()

    def updateWidgets(self):
        super(EmasMobileThemeSettingsForm, self).updateWidgets()


class EmasMobileThemeSettingsControlPanel(controlpanel.ControlPanelFormWrapper):
    form = EmasMobileThemeSettingsForm
