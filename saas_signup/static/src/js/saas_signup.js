odoo.define('saas_signup.main', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');

    publicWidget.registry.SaasSignup = publicWidget.Widget.extend({
        selector: '.saas_signup_page',
        events: {
            'input #port': '_onPortChange',
            'input #database_identifier': '_onIdentifierChange',
            'input #subdomain': '_onSubdomainChange',
            'change input[name="plan_id"]': '_onPlanChange',
        },

        start: function () {
            this._super.apply(this, arguments);
            this._initializePlanSelection();
        },

        _initializePlanSelection: function () {
            // Make radio buttons visible and working
            var planRadios = document.querySelectorAll('input[name="plan_id"]');
            planRadios.forEach(function(radio) {
                radio.style.display = 'block';
                radio.style.marginTop = '10px';
            });
        },

        _onPortChange: function (ev) {
            var self = this;
            var port = $(ev.currentTarget).val();
            var $feedback = $('#port-feedback');

            if (!port) {
                $feedback.html('').removeClass('available unavailable');
                return;
            }

            // Validate port range
            var portNum = parseInt(port);
            if (portNum < 8081 || portNum > 65535) {
                $feedback.html('<i class="fa fa-times"></i> Port must be between 8081 and 65535')
                        .removeClass('available')
                        .addClass('unavailable');
                return;
            }

            // Show checking message
            $feedback.html('<i class="fa fa-spinner fa-spin"></i> Checking port availability...')
                     .removeClass('available unavailable');

            // Debounce the check
            clearTimeout(this.portTimeout);
            this.portTimeout = setTimeout(function () {
                self._checkPortAvailability(port);
            }, 500);
        },

        _onIdentifierChange: function (ev) {
            var identifier = $(ev.currentTarget).val();
            var $feedback = $('#port-feedback');

            if (!identifier) {
                $feedback.html('');
                return;
            }
        },

        _checkPortAvailability: function (port) {
            var self = this;
            this._rpc({
                route: '/saas/check-port',
                params: { port: port }
            }).then(function (result) {
                var $feedback = $('#port-feedback');
                if (result.available) {
                    $feedback.html('<i class="fa fa-check"></i> ' + result.message)
                            .removeClass('unavailable')
                            .addClass('available');
                } else {
                    $feedback.html('<i class="fa fa-times"></i> ' + result.message)
                            .removeClass('available')
                            .addClass('unavailable');
                }
            });
        },

        _onSubdomainChange: function (ev) {
            var self = this;
            var subdomain = $(ev.currentTarget).val().toLowerCase().replace(/[^a-z0-9]/g, '');
            var $input = $(ev.currentTarget);
            var $preview = $('#subdomain-preview');
            var $feedback = $('#subdomain-feedback');
            var $loading = $('#subdomain-loading');
            var $available = $('#subdomain-available');
            var $taken = $('#subdomain-taken');

            // Update cleaned value
            if ($input.val() !== subdomain) {
                $input.val(subdomain);
            }

            // Update preview
            $preview.text(subdomain || 'yoursubdomain');

            if (!subdomain || subdomain.length < 3) {
                this._hideAllIcons();
                $feedback.html('').removeClass('text-success text-danger');
                if (subdomain && subdomain.length < 3) {
                    $feedback.html('<small class="text-warning">Subdomain must be at least 3 characters</small>');
                }
                return;
            }

            // Show loading
            this._hideAllIcons();
            $loading.show();
            $feedback.html('<small class="text-muted">Checking availability...</small>');

            // Debounce the check
            clearTimeout(this.subdomainTimeout);
            this.subdomainTimeout = setTimeout(function () {
                self._checkSubdomainAvailability(subdomain);
            }, 500);
        },

        _hideAllIcons: function () {
            $('#subdomain-loading').hide();
            $('#subdomain-available').hide();
            $('#subdomain-taken').hide();
        },

        _checkSubdomainAvailability: function (subdomain) {
            var self = this;
            this._rpc({
                route: '/saas/check-subdomain',
                params: { subdomain: subdomain }
            }).then(function (result) {
                self._hideAllIcons();
                var $feedback = $('#subdomain-feedback');
                
                if (result.available) {
                    $('#subdomain-available').show();
                    $feedback.html('<small class="text-success"><i class="fa fa-check-circle"></i> ' + result.message + '</small>');
                    $('#subdomain').removeClass('is-invalid').addClass('is-valid');
                } else {
                    $('#subdomain-taken').show();
                    $feedback.html('<small class="text-danger"><i class="fa fa-exclamation-circle"></i> ' + result.message + '</small>');
                    $('#subdomain').removeClass('is-valid').addClass('is-invalid');
                }
            }).catch(function (error) {
                self._hideAllIcons();
                $('#subdomain-feedback').html('<small class="text-danger">Error checking subdomain</small>');
            });
        },

        _onPlanChange: function (ev) {
            // Highlight selected plan
            $('.plan_card').removeClass('selected');
            $(ev.currentTarget).closest('.form-check').find('.plan_card').addClass('selected');
        },
    });

    return publicWidget.registry.SaasSignup;
});