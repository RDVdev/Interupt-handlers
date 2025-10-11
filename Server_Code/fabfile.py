from fabric import task, Connection
import os


# ============= CONFIGURATION =============
SERVER_IP = 'winterdewserver.eastus2.cloudapp.azure.com'
SERVER_USER = 'winterdew'
SERVER_PASSWORD = os.getenv('SERVER_PASSWORD')  # Or use --prompt-for-login-password


LOCAL_APP_DIR = './app'              # Local folder name
REMOTE_APP_NAME = 'esw-server'       # Remote folder name
REMOTE_APP_DIR = f'/home/{SERVER_USER}/{REMOTE_APP_NAME}'
SERVICE_NAME = 'esw-server'
FLASK_PORT = 8000
# =========================================


def get_connection():
    """Create and return a connection to the server"""
    return Connection(
        host=SERVER_IP,
        user=SERVER_USER,
        connect_kwargs={'password': SERVER_PASSWORD}
    )



@task
def setup(c):
    """
    Initial server setup - Run this ONCE before first deployment
    Sets up systemd service to run even after logout
    """
    print("🔧 Starting initial server setup...")
    conn = get_connection()
    
    # Install required system packages
    print("📦 Installing system packages...")
    conn.sudo('apt update', hide=False)
    conn.sudo('apt install -y python3 python3-pip python3-venv', hide=False)
    
    # Create application directory
    print(f"📁 Creating application directory: {REMOTE_APP_DIR}")
    conn.run(f'mkdir -p {REMOTE_APP_DIR}')
    
    # Create virtual environment
    print("🐍 Creating Python virtual environment...")
    conn.run(f'python3 -m venv {REMOTE_APP_DIR}/venv')
    
    # Create systemd service file
    print("⚙️  Creating systemd service...")
    service_content = f"""[Unit]
Description=ESW Flask Server
After=network.target


[Service]
Type=simple
User={SERVER_USER}
WorkingDirectory={REMOTE_APP_DIR}
Environment="PATH={REMOTE_APP_DIR}/venv/bin"
Environment="FLASK_APP=app.py"
Environment="FLASK_ENV=production"
ExecStart={REMOTE_APP_DIR}/venv/bin/python -m flask run --host=0.0.0.0 --port={FLASK_PORT}
Restart=always
RestartSec=3


[Install]
WantedBy=multi-user.target
"""
    
    # Write service file to temp location, then move with sudo
    conn.run(f"echo '{service_content}' > /tmp/{SERVICE_NAME}.service")
    conn.sudo(f'mv /tmp/{SERVICE_NAME}.service /etc/systemd/system/{SERVICE_NAME}.service')
    
    # Reload systemd and enable service
    conn.sudo('systemctl daemon-reload')
    conn.sudo(f'systemctl enable {SERVICE_NAME}')
    
    print("✅ Setup complete! Now run: fab deploy")



@task
def deploy(c):
    """
    Deploy/redeploy application from local 'app' folder to remote 'esw-server'
    Syncs files and restarts the service
    """
    print("🚀 Starting deployment...")
    conn = get_connection()
    
    # Check if local app directory exists
    if not os.path.exists(LOCAL_APP_DIR):
        print(f"❌ Error: Local directory '{LOCAL_APP_DIR}' not found!")
        return
    
    # Upload files
    print(f"📤 Uploading files from {LOCAL_APP_DIR}/ → {REMOTE_APP_DIR}/")
    
    # Walk through local directory and upload all files
    for root, dirs, files in os.walk(LOCAL_APP_DIR):
        # Skip unwanted directories
        dirs[:] = [d for d in dirs if d not in ['venv', '__pycache__', '.git']]
        
        # Get relative path from LOCAL_APP_DIR
        rel_path = os.path.relpath(root, LOCAL_APP_DIR)
        
        # Create remote directory structure
        if rel_path != '.':
            remote_dir = f'{REMOTE_APP_DIR}/{rel_path}'
            conn.run(f'mkdir -p {remote_dir}')
        
        # Upload each file
        for filename in files:
            # Skip unwanted files
            if filename.endswith(('.pyc', '.pyo', '.log')) or filename == '.env':
                continue
            
            local_file = os.path.join(root, filename)
            
            if rel_path == '.':
                remote_file = f'{REMOTE_APP_DIR}/{filename}'
            else:
                remote_file = f'{REMOTE_APP_DIR}/{rel_path}/{filename}'
            
            print(f"  Uploading: {filename}")
            conn.put(local_file, remote_file)
    
    print("✅ All files uploaded successfully!")
    
    # Install/update Python dependencies
    print("📚 Installing Python dependencies...")
    result = conn.run(f'test -f {REMOTE_APP_DIR}/requirements.txt', warn=True)
    if result.ok:
        conn.run(f'{REMOTE_APP_DIR}/venv/bin/pip install -r {REMOTE_APP_DIR}/requirements.txt', hide=False)
    else:
        print("⚠️  No requirements.txt found, skipping pip install")
    
    # Restart the service
    print("🔄 Restarting service...")
    conn.sudo(f'systemctl restart {SERVICE_NAME}')
    
    # Check service status
    print("📊 Service status:")
    conn.sudo(f'systemctl status {SERVICE_NAME} --no-pager', hide=False, warn=True)
    
    print(f"\n✅ Deployment complete!")
    print(f"🌐 Application running at: http://{SERVER_IP}:{FLASK_PORT}")
    print(f"📝 View logs: fab logs")



@task
def logs(c):
    """View real-time application logs"""
    print("📋 Viewing logs (Ctrl+C to exit)...")
    conn = get_connection()
    conn.sudo(f'journalctl -u {SERVICE_NAME} -f --no-pager', hide=False)



@task
def status(c):
    """Check application status"""
    print("📊 Checking service status...")
    conn = get_connection()
    conn.sudo(f'systemctl status {SERVICE_NAME} --no-pager', hide=False)



@task
def stop(c):
    """Stop the application"""
    print("🛑 Stopping application...")
    conn = get_connection()
    conn.sudo(f'systemctl stop {SERVICE_NAME}')
    print("✅ Application stopped")



@task
def start(c):
    """Start the application"""
    print("▶️  Starting application...")
    conn = get_connection()
    conn.sudo(f'systemctl start {SERVICE_NAME}')
    print("✅ Application started")



@task
def restart(c):
    """Restart the application"""
    print("🔄 Restarting application...")
    conn = get_connection()
    conn.sudo(f'systemctl restart {SERVICE_NAME}')
    print("✅ Application restarted")



@task
def ssh(c):
    """Open SSH session to the server"""
    print(f"🔌 Connecting to {SERVER_USER}@{SERVER_IP}...")
    c.local(f'ssh {SERVER_USER}@{SERVER_IP}')



@task
def clean(c):
    """Remove application and service from server"""
    print("🗑️  This will completely remove the application. Are you sure?")
    response = input("Type 'yes' to confirm: ")
    if response.lower() != 'yes':
        print("❌ Cancelled")
        return
    
    conn = get_connection()
    print("Stopping and removing service...")
    conn.sudo(f'systemctl stop {SERVICE_NAME}', warn=True)
    conn.sudo(f'systemctl disable {SERVICE_NAME}', warn=True)
    conn.sudo(f'rm /etc/systemd/system/{SERVICE_NAME}.service', warn=True)
    conn.sudo('systemctl daemon-reload')
    
    print("Removing application directory...")
    conn.run(f'rm -rf {REMOTE_APP_DIR}', warn=True)
    
    print("✅ Application removed from server")



@task
def info(c):
    """Display deployment information"""
    print("\n" + "="*50)
    print("📋 DEPLOYMENT CONFIGURATION")
    print("="*50)
    print(f"Server:           {SERVER_USER}@{SERVER_IP}")
    print(f"Local folder:     {LOCAL_APP_DIR}")
    print(f"Remote folder:    {REMOTE_APP_DIR}")
    print(f"Service name:     {SERVICE_NAME}")
    print(f"Port:             {FLASK_PORT}")
    print(f"Application URL:  http://{SERVER_IP}:{FLASK_PORT}")
    print("="*50 + "\n")
