import os

# Define your module names
modules = [
    'crop',         # Crop & Location Management
    'model',        # Model Management
    'analytics',    # Performance Analytics
    'data'          # Soil & Weather Data Management
]

# Files to create in each module
files = [
    '__init__.py',
    'forms.py',
    'models.py',
    'routes.py',
    'util.py'
]

# Base directory for modules
base_dir = os.path.join(os.getcwd(), 'apps')

def create_module_structure():
    for module in modules:
        module_path = os.path.join(base_dir, module)

        try:
            os.makedirs(module_path, exist_ok=True)
            print(f"[+] Created directory: {module_path}")

            for file_name in files:
                file_path = os.path.join(module_path, file_name)

                if not os.path.exists(file_path):
                    with open(file_path, 'w') as f:
                        f.write(f"# {file_name} for {module} module\n")
                    print(f"    - Created file: {file_path}")
                else:
                    print(f"    - File already exists: {file_path}")

        except Exception as e:
            print(f"[!] Error creating module {module}: {e}")

if __name__ == '__main__':
    create_module_structure()
