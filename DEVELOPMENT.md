# 🛠️ Development and Customization Guide

This guide covers how to develop, customize, and extend the Odoo 19 SaaS Multi-Tenancy Platform.

## 🏗️ Project Structure

```
Odoo19-Saas-Multi-tenancy/
├── saas_signup/                    # Main SaaS module
│   ├── __init__.py                # Module initialization
│   ├── __manifest__.py            # Module manifest
│   ├── controllers/               # HTTP routes and API endpoints
│   │   ├── __init__.py
│   │   └── main.py               # Main controller logic
│   ├── models/                    # Data models
│   │   ├── __init__.py
│   │   ├── saas_client.py         # Tenant client model
│   │   ├── saas_config.py         # Configuration model
│   │   ├── saas_subscription.py   # Subscription plans
│   │   └── saas_usage.py          # Usage tracking
│   ├── views/                     # UI views and templates
│   │   ├── saas_signup_templates.xml   # Signup forms
│   │   ├── saas_config_views.xml       # Configuration views
│   │   ├── saas_client_views.xml       # Tenant management
│   │   └── website_menu_views.xml      # Website menus
│   ├── static/                    # CSS, JS, images
│   │   ├── src/css/              # Stylesheets
│   │   ├── src/js/               # JavaScript files
│   │   └── images/               # Images and icons
│   ├── data/                     # Default data
│   │   ├── subscription_plans_data.xml  # Default plans
│   │   └── saas_config_data.xml         # Default config
│   ├── security/                 # Access control
│   │   └── ir.model.access.csv
│   ├── tests/                    # Test files
│   └── utils/                    # Helper utilities
├── config/
│   └── odoo.conf                 # Odoo configuration
├── docker-compose.yml            # Docker services
├── SETUP.md                      # Installation guide
├── DEVELOPMENT.md                # This file
└── README.md                     # Main documentation
```

## 🔧 Development Environment Setup

### Prerequisites
- Docker and Docker Compose
- Git
- Python 3.8+ (for local development)
- Odoo 19.0 source (optional, for debugging)

### Setting Up Development Environment

1. **Clone and Setup**:
```bash
git clone https://github.com/sfowooza/Odoo19-Saas-Multi-tenancy.git
cd Odoo19-Saas-Multi-tenancy
```

2. **Start Development Environment**:
```bash
# Start services
docker-compose up -d

# Enter the Odoo container
docker-compose exec odoo19 bash
```

3. **Install Development Tools**:
```bash
# Inside the container
pip install ipython pudb
```

### Development Workflow

1. **Create a Feature Branch**:
```bash
git checkout -b feature/your-feature-name
```

2. **Make Changes**:
   - Edit files in `saas_signup/`
   - Test your changes
   - Ensure code quality

3. **Test Your Changes**:
```bash
# Restart Odoo to load changes
docker-compose restart odoo19

# Or run upgrade command
docker-compose exec odoo19 odoo -d db1 -u saas_signup --stop-after-init
```

4. **Commit Changes**:
```bash
git add .
git commit -m "feat: add your feature description"
git push origin feature/your-feature-name
```

## 🎯 Customization Guide

### Adding New Features

#### 1. Adding New Models

```python
# saas_signup/models/custom_model.py
from odoo import models, fields, api

class CustomModel(models.Model):
    _name = 'saas.custom.model'
    _description = 'Custom SaaS Model'

    name = fields.Char(string='Name', required=True)
    client_id = fields.Many2one('saas.client', string='Client')
    custom_field = fields.Text(string='Custom Field')
    created_date = fields.Datetime(string='Created Date', default=fields.Datetime.now)

    @api.model
    def create_custom_record(self, values):
        """Custom creation logic"""
        return self.create(values)
```

Don't forget to add it to `__init__.py`:
```python
# saas_signup/models/__init__.py
from . import saas_client
from . import saas_config
from . import saas_subscription
from . import custom_model  # Add your new model
```

#### 2. Adding New Views

```xml
<!-- saas_signup/views/custom_views.xml -->
<odoo>
    <data>
        <!-- List View -->
        <record id="view_custom_model_list" model="ir.ui.view">
            <field name="name">Custom Model List</field>
            <field name="model">saas.custom.model</field>
            <field name="arch" type="xml">
                <tree string="Custom Models">
                    <field name="name"/>
                    <field name="client_id"/>
                    <field name="created_date"/>
                </tree>
            </field>
        </record>

        <!-- Form View -->
        <record id="view_custom_model_form" model="ir.ui.view">
            <field name="name">Custom Model Form</field>
            <field name="model">saas.custom.model</field>
            <field name="arch" type="xml">
                <form string="Custom Model">
                    <sheet>
                        <group>
                            <field name="name"/>
                            <field name="client_id"/>
                            <field name="custom_field"/>
                        </group>
                    </sheet>
                </form>
            </field>
        </record>

        <!-- Action -->
        <record id="action_custom_model" model="ir.actions.act_window">
            <field name="name">Custom Models</field>
            <field name="res_model">saas.custom.model</field>
            <field name="view_mode">tree,form</field>
        </record>
    </data>
</odoo>
```

#### 3. Adding New API Endpoints

```python
# saas_signup/controllers/main.py
class SaasSignupController(http.Controller):

    @http.route('/api/custom', type='json', auth='public', methods=['POST'], csrf=False)
    def custom_api_endpoint(self, **kwargs):
        """Custom API endpoint"""
        try:
            # Your custom logic here
            result = {
                'status': 'success',
                'data': kwargs
            }
            return result
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/saas/custom-page', type='http', auth='public', website=True)
    def custom_page(self, **kwargs):
        """Custom website page"""
        return request.render('saas_signup.custom_template', kwargs)
```

#### 4. Extending Existing Templates

```xml
<!-- saas_signup/views/custom_templates.xml -->
<odoo>
    <data>
        <!-- Extend signup form -->
        <template id="custom_signup_form" inherit_id="saas_signup.signup_form">
            <xpath expr="//form[@id='signupForm']//div[@class='form-group']" position="after">
                <div class="form-group">
                    <label class="form-label">Custom Field</label>
                    <input type="text" name="custom_field" class="form-control" required="required"/>
                    <small class="form-text">Enter your custom value</small>
                </div>
            </xpath>
        </template>
    </data>
</odoo>
```

### Customizing Tenant Creation

#### 1. Extend Client Model

```python
# saas_signup/models/saas_client.py
class SaasClient(models.Model):
    _inherit = 'saas.client'

    # Add custom fields
    custom_domain = fields.Char(string='Custom Domain')
    custom_logo = fields.Binary(string='Company Logo')
    custom_theme = fields.Selection([
        ('light', 'Light Theme'),
        ('dark', 'Dark Theme'),
        ('custom', 'Custom Theme')
    ], string='Theme', default='light')

    def create_tenant_container(self):
        """Override tenant creation with custom logic"""
        # Call parent method
        result = super().create_tenant_container()

        # Add custom logic
        self._setup_custom_domain()
        self._apply_custom_theme()

        return result

    def _setup_custom_domain(self):
        """Setup custom domain if provided"""
        if self.custom_domain:
            # Your domain setup logic here
            pass

    def _apply_custom_theme(self):
        """Apply custom theme to tenant"""
        if self.custom_theme == 'dark':
            # Apply dark theme
            pass
```

#### 2. Custom Configuration Options

```xml
<!-- saas_signup/data/saas_config_data.xml -->
<odoo>
    <data noupdate="1">
        <record id="config_default" model="saas.configuration">
            <field name="name">Default Configuration</field>
            <field name="deployment_mode">localhost</field>
            <field name="master_port">7001</field>
            <field name="tenant_port_start">8000</field>
            <field name="tenant_port_end">9000</field>

            <!-- Custom fields -->
            <field name="auto_backup">True</field>
            <field name="backup_retention_days">30</field>
            <field name="enable_monitoring">True</field>
            <field name="max_tenant_memory">2048</field>
            <field name="max_tenant_cpu">2</field>
        </record>
    </data>
</odoo>
```

### Adding Custom Subscription Plans

```xml
<!-- saas_signup/data/subscription_plans_data.xml -->
<odoo>
    <data noupdate="1">
        <!-- Custom Enterprise Plan -->
        <record id="plan_enterprise_plus" model="saas.subscription">
            <field name="name">Enterprise Plus</field>
            <field name="description">Advanced features for large organizations</field>
            <field name="price">299.99</field>
            <field name="billing_cycle">monthly</field>
            <field name="max_users">200</field>
            <field name="storage_gb">200</field>
            <field name="enable_trial">False</field>
            <field name="sequence">50</field>

            <!-- Custom features -->
            <field name="enable_api_access">True</field>
            <field name="enable_white_label">True</field>
            <field name="enable_priority_support">True</field>
        </record>
    </data>
</odoo>
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
docker-compose exec odoo19 odoo -d db1 --test-enable --stop-after-init

# Run specific module tests
docker-compose exec odoo19 odoo -d db1 --test-enable -i saas_signup --stop-after-init

# Run specific test class
docker-compose exec odoo19 python -m pytest tests/test_saas_client.py -v
```

### Writing Tests

```python
# saas_signup/tests/test_saas_client.py
from odoo.tests import TransactionCase

class TestSaasClient(TransactionCase):

    def setUp(self):
        super().setUp()
        self.client_model = self.env['saas.client']
        self.subscription_model = self.env['saas.subscription']

    def test_client_creation(self):
        """Test basic client creation"""
        client_vals = {
            'name': 'Test Client',
            'database_name': 'test_client_db',
            'admin_email': 'test@example.com',
            'subscription_id': self.subscription_model.search([], limit=1).id
        }

        client = self.client_model.create(client_vals)
        self.assertEqual(client.name, 'Test Client')
        self.assertEqual(client.state, 'draft')

    def test_tenant_creation(self):
        """Test tenant container creation"""
        # Create client first
        client = self.client_model.create({
            'name': 'Test Tenant',
            'database_name': 'test_tenant_db',
            'admin_email': 'tenant@example.com'
        })

        # Test tenant creation
        result = client.create_tenant_container()
        self.assertTrue(result)
        self.assertEqual(client.state, 'active')
```

## 🎨 Frontend Customization

### Custom CSS

```css
/* saas_signup/static/src/css/custom.css */
.custom-signup-form {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 15px;
    padding: 30px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
}

.custom-plan-card {
    transition: all 0.3s ease;
    border: 2px solid transparent;
}

.custom-plan-card:hover {
    transform: translateY(-5px);
    border-color: #667eea;
    box-shadow: 0 15px 40px rgba(0,0,0,0.15);
}
```

### Custom JavaScript

```javascript
// saas_signup/static/src/js/custom.js
odoo.define('saas_signup.custom', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');

    publicWidget.registry.SaaSCustomWidget = publicWidget.Widget.extend({
        selector: '.custom-signup-form',

        start: function () {
            this._super.apply(this, arguments);
            this.initializeCustomFeatures();
        },

        initializeCustomFeatures: function () {
            // Add custom JavaScript functionality
            this.setupFormValidation();
            this.setupPlanSelection();
        },

        setupFormValidation: function () {
            var self = this;
            this.$('form').on('submit', function (e) {
                if (!self.validateForm()) {
                    e.preventDefault();
                }
            });
        },

        setupPlanSelection: function () {
            var self = this;
            this.$('.plan-card').on('click', function () {
                self.$('.plan-card').removeClass('selected');
                $(this).addClass('selected');
                self.updateSubmitButton();
            });
        }
    });

    return {
        'SaaSCustomWidget': publicWidget.registry.SaaSCustomWidget
    };
});
```

## 🚀 Performance Optimization

### Database Optimization

```python
# Add indexes for better performance
class SaasClient(models.Model):
    _name = 'saas.client'

    # Add indexes in _auto_init
    def _auto_init(self):
        """Add database indexes"""
        res = super()._auto_init()

        # Create custom indexes
        self._cr.execute("""
            CREATE INDEX IF NOT EXISTS idx_saas_client_email
            ON saas_client(admin_email);

            CREATE INDEX IF NOT EXISTS idx_saas_client_state
            ON saas_client(state);

            CREATE INDEX IF NOT EXISTS idx_saas_client_created_date
            ON saas_client(create_date);
        """)

        return res
```

### Caching

```python
# Add caching for expensive operations
from odoo.tools.cache import cache

class SaasClient(models.Model):
    @cache()
    def get_tenant_statistics(self, client_id):
        """Cached tenant statistics"""
        client = self.browse(client_id)
        return {
            'users_count': client.users_count,
            'storage_used': client.storage_used,
            'last_active': client.last_active_date,
        }
```

## 🔒 Security Considerations

### Input Validation

```python
# Always validate user input
@http.route('/api/tenant/create', type='json', auth='public', methods=['POST'])
def create_tenant_api(self, **kwargs):
    """Secure tenant creation API"""
    # Validate required fields
    required_fields = ['name', 'email', 'plan_id']
    for field in required_fields:
        if not kwargs.get(field):
            return {
                'error': 'Missing required field: {}'.format(field)
            }

    # Sanitize inputs
    name = re.sub(r'[^\w\s-]', '', kwargs.get('name', ''))
    email = re.sub(r'[^\w@.-]', '', kwargs.get('email', ''))

    # Additional validation
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return {'error': 'Invalid email address'}
```

### Access Control

```python
# Proper access control
class SaasClientController(http.Controller):

    @http.route('/saas/admin/tenants', type='http', auth='user')
    def admin_tenants(self, **kwargs):
        """Admin only endpoint"""
        # Check if user has admin rights
        if not self.env.user.has_group('base.group_system'):
            return request.render('website.404')

        # Admin logic here
        return request.render('saas_signup.admin_tenants', {})
```

## 📚 Additional Resources

- [Odoo Documentation](https://www.odoo.com/documentation/)
- [Odoo Developer Documentation](https://www.odoo.com/documentation/developer/)
- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

This development guide should help you customize and extend the SaaS platform according to your specific requirements.