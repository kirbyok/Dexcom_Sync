# Dexcom Sync System - Project Overview

## 🎯 Project Summary

A full-featured Python web application that syncs Dexcom CGM (Continuous Glucose Monitor) data to multiple platforms with a retro industrial web interface.

## 📋 What You Have

### Complete Application Stack
✅ **Backend**: Flask web application with RESTful API  
✅ **Database**: SQLAlchemy ORM with SQLite (MySQL support included)  
✅ **Authentication**: Flask-Login with bcrypt password hashing  
✅ **Encryption**: Fernet symmetric encryption for sensitive data  
✅ **Scheduling**: APScheduler for automated background syncing  
✅ **Docker**: Complete containerization with docker-compose  

### API Integrations
✅ **Dexcom API**: OAuth 2.0 authentication + glucose data fetching  
✅ **Nightscout**: Upload to Nightscout CGM platform  
✅ **MySQL**: Direct database storage  
✅ **Airtable**: Cloud spreadsheet-database sync  
✅ **Google Sheets**: Spreadsheet integration via service accounts  

### Web Interface
✅ **Dashboard**: Real-time glucose monitoring with 24h charts  
✅ **Settings**: Complete configuration management  
✅ **Login**: Secure authentication system  
✅ **Theme**: Retro industrial design (orange/black color scheme)  

### Security Features
✅ Encrypted credential storage  
✅ OAuth token management  
✅ Password hashing  
✅ Session management  
✅ HTTPS-ready (via Cloudflared)  

### Documentation
✅ Comprehensive README.md  
✅ Quick Start Guide  
✅ Contributing Guidelines  
✅ Setup Scripts (Windows & Linux)  
✅ Inline code documentation  

### Utility Scripts
✅ Database backup/restore tool  
✅ Key generation script  
✅ Connector testing script  

## 📁 File Structure

```
Dexcom_Sync/
├── app.py                          # Main Flask application
├── config.py                       # Configuration with encryption
├── models.py                       # Database models (SQLAlchemy)
├── dexcom_client.py               # Dexcom API integration
├── sync_manager.py                # Sync orchestration
├── scheduler.py                   # Background task scheduler
│
├── connectors/                    # Data destination connectors
│   ├── __init__.py
│   ├── nightscout_connector.py
│   ├── mysql_connector.py
│   ├── airtable_connector.py
│   └── sheets_connector.py
│
├── templates/                     # HTML templates
│   ├── base.html                 # Base template with retro theme
│   ├── login.html                # Login page
│   ├── dashboard.html            # Main dashboard
│   └── settings.html             # Configuration page
│
├── scripts/                       # Utility scripts
│   ├── backup_db.py              # Database backup tool
│   ├── generate_keys.py          # Key generation
│   └── test_connectors.py        # Test destinations
│
├── data/                          # Database storage (Docker volume)
├── logs/                          # Application logs
│
├── requirements.txt               # Python dependencies
├── Dockerfile                     # Docker image definition
├── docker-compose.yml            # Docker orchestration
├── .env.example                  # Environment template
├── .gitignore                    # Git ignore rules
├── .dockerignore                 # Docker ignore rules
│
├── README.md                      # Main documentation
├── QUICKSTART.md                 # Quick start guide
├── CONTRIBUTING.md               # Contribution guidelines
├── LICENSE                        # MIT License
├── setup.sh                      # Linux setup script
├── setup.bat                     # Windows setup script
└── cloudflared-config.yml        # Cloudflared configuration
```

## 🚀 Key Features

### 1. Automated Data Flow
```
Dexcom API → Application → [Nightscout, MySQL, Airtable, Sheets]
   (OAuth)     (Every 5min)    (Parallel sync to enabled destinations)
```

### 2. Data Model
- **GlucoseReading**: Stores readings with sync status
- **Settings**: Encrypted configuration storage
- **SyncLog**: Audit trail of all sync operations
- **User**: Authentication (bcrypt hashed passwords)

### 3. Security Layers
```
User → HTTPS (Cloudflared) → Flask App → Encrypted DB
                                    ↓
                              OAuth Tokens (encrypted)
                              API Keys (encrypted)
                              Passwords (encrypted)
```

## 🔧 Technology Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11+, Flask 3.0 |
| **Database** | SQLAlchemy ORM, SQLite/MySQL |
| **Auth** | Flask-Login, Bcrypt |
| **Encryption** | Cryptography (Fernet) |
| **Scheduling** | APScheduler |
| **API Clients** | requests, pyairtable, google-api-python-client, pymysql |
| **Frontend** | HTML5, CSS3, Chart.js |
| **Container** | Docker, docker-compose |
| **Server** | Gunicorn (production) |

## 📊 Data Flow

### Reading Sync Process
1. **Fetch**: Scheduler triggers `sync_readings()` every 5 minutes
2. **Retrieve**: Dexcom API called for new readings since last sync
3. **Store**: Readings saved to local database
4. **Distribute**: Parallel upload to all configured destinations
5. **Track**: Sync status updated for each reading/destination
6. **Log**: Operation logged to SyncLog table

### OAuth Flow (Dexcom)
1. User clicks "Authorize Dexcom"
2. Redirect to Dexcom OAuth login
3. User authenticates and authorizes
4. Callback receives authorization code
5. Exchange code for access + refresh tokens
6. Tokens encrypted and stored in database
7. Automatic token refresh when needed

## 🎨 UI Design

### Theme: Retro Industrial
- **Colors**: Orange (#ff6b00) on dark (#1a1a1a)
- **Font**: Courier New (monospace)
- **Style**: High-tech terminal aesthetic
- **Elements**: 
  - Glowing borders
  - Status indicators with pulse animation
  - Uppercase labels
  - Terminal-style panels

### Responsive Layout
- Mobile-friendly
- Collapsible sections
- Scrollable tables
- Touch-friendly buttons

## 🔐 Security Considerations

### What's Encrypted
- Dexcom OAuth tokens
- Nightscout API secrets
- MySQL passwords
- Airtable API keys
- Google Sheets credentials

### What's Hashed
- User passwords (bcrypt with salt)

### What's Protected
- Settings page (login required)
- API endpoints (login required)
- Database files (filesystem permissions)

## 🐳 Docker Architecture

```yaml
Services:
  dexcom-sync:
    - Flask application
    - Gunicorn server (2 workers)
    - Port 5000 exposed
    - Health checks enabled
    - Auto-restart policy
    
Volumes:
  - ./data:/app/data         # Database persistence
  - ./logs:/app/logs         # Log persistence
  
Networks:
  - Default bridge network
  - Can add custom networks for multi-container setups
```

## 📈 Performance & Scalability

### Current Design
- **Sync Interval**: 5 minutes (configurable)
- **Workers**: 2 Gunicorn workers
- **Database**: SQLite (sufficient for single-user)
- **Concurrency**: Parallel destination uploads

### Scaling Options
- Increase sync interval for lower API usage
- Switch to PostgreSQL/MySQL for multi-user
- Add Redis for caching
- Deploy multiple instances behind load balancer
- Use Celery for distributed task processing

## 🧪 Testing Capabilities

### Manual Testing
- Dashboard: View readings and charts
- Manual Sync: Trigger on-demand sync
- Settings: Configure and test destinations

### Automated Testing
- `scripts/test_connectors.py`: Test all destinations
- Health endpoint: `/health`
- Logs: Check `logs/` directory

## 🔄 Maintenance

### Regular Tasks
- Database backups (use `scripts/backup_db.py`)
- Log rotation
- Dependency updates
- Security patches

### Monitoring
- Sync logs on dashboard
- Docker container health
- Disk space (database growth)
- API rate limits

## 🎯 Use Cases

1. **Personal Health Tracking**: Individual monitoring glucose data
2. **Caregiver Support**: Share data with family via Nightscout
3. **Data Analysis**: Export to Sheets/Airtable for analysis
4. **Clinical Studies**: Store data in MySQL for research
5. **Backup**: Multiple redundant copies of health data

## 🔮 Future Enhancement Ideas

### Feature Additions
- [ ] Email/SMS alerts for high/low glucose
- [ ] Multi-user support with separate accounts
- [ ] Data export (CSV, JSON)
- [ ] Statistical analysis dashboard
- [ ] Mobile app (companion)
- [ ] Insulin tracking integration
- [ ] Meal logging
- [ ] Webhooks for external integrations

### Technical Improvements
- [ ] Unit test suite
- [ ] Integration tests
- [ ] Performance optimization
- [ ] Caching layer (Redis)
- [ ] Queue system (Celery)
- [ ] Kubernetes deployment configs
- [ ] CI/CD pipeline

## 📚 Learning Resources

### Understand the Code
1. Start with `app.py` - main application entry
2. Review `models.py` - understand data structure
3. Explore `dexcom_client.py` - see OAuth implementation
4. Check `connectors/` - learn destination integrations
5. Read `sync_manager.py` - understand sync logic

### Dexcom API
- [Developer Portal](https://developer.dexcom.com)
- [API Documentation](https://developer.dexcom.com/overview)
- OAuth 2.0 flow
- Rate limits and best practices

### Flask Resources
- [Flask Documentation](https://flask.palletsprojects.com/)
- Flask-Login
- Flask-SQLAlchemy
- Jinja2 templates

## 🆘 Support

### Common Issues
1. **Can't connect to Dexcom**: Check credentials and redirect URI
2. **Data not syncing**: Verify destination configuration
3. **Port conflicts**: Change port in docker-compose.yml
4. **Permission errors**: Check file permissions on data/

### Debug Mode
Enable debug output:
```env
FLASK_DEBUG=True
```

View logs:
```bash
docker-compose logs -f
```

## ✅ Production Checklist

Before deploying to production:

- [ ] Change default admin password
- [ ] Generate strong encryption keys
- [ ] Configure SSL (Cloudflared)
- [ ] Set `FLASK_DEBUG=False`
- [ ] Configure firewall rules
- [ ] Setup automated backups
- [ ] Test all destinations
- [ ] Monitor initial sync operations
- [ ] Document your specific setup
- [ ] Create recovery procedures

## 📄 License

MIT License - Open source, free to use and modify

## 🙏 Credits

- **Dexcom** for CGM technology and API
- **Nightscout** community for open-source CGM platform
- **Flask** team for excellent web framework
- **Chart.js** for visualization library

---

## Next Steps

1. ✅ **Setup**: Run `setup.bat` (Windows) or `setup.sh` (Linux)
2. ✅ **Configure**: Edit `.env` with your credentials
3. ✅ **Deploy**: Run `docker-compose up -d`
4. ✅ **Access**: Open http://localhost:5000
5. ✅ **Authorize**: Connect your Dexcom account
6. ✅ **Configure**: Setup your data destinations
7. ✅ **Monitor**: Watch your data sync automatically

**You now have a production-ready Dexcom sync system!** 🎉
