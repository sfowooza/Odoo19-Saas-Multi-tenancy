# -*- coding: utf-8 -*-

from odoo import models, fields

class SaasMasterPasswordWizard(models.TransientModel):
    _name = 'saas.master.password.wizard'
    _description = 'SaaS Master Password Information Wizard'

    # This is a transient model (wizard) - no fields needed
    # It just displays static information
    pass
