import zipfile
import hashlib
import os
from io import BytesIO
from datetime import datetime
import subprocess
import shlex

product_list =  ['DD', 'ECS', 'IDRAC', 'OS10', 'PPCR', 'PPDM']

deploy_file_list = [
    "src/DCO-DailyCheck.py",
    "src/common/__init__.py",
    "src/common/password_manager.py",
    "src/common/functions.py",
    "src/common/DCOconfig.py",
    "src/common/DCOreport.py",
    "src/TEMPLATEconfig.json",
    "src/config_tool.py"
]

for product in product_list:
	deploy_file_list.append(f'src/{product}/__init__.py')
	deploy_file_list.append(f'src/{product}/{product}getinfo.py')
	deploy_file_list.append(f'src/{product}/{product}processinfo.py')
	deploy_file_list.append(f'src/{product}/{product}createreportDC.py')
	deploy_file_list.append(f'src/{product}/{product}createreportDCI.py')

# Function to compute SHA-256 hash of a file
def compute_sha256(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        # Read file in chunks to handle large files efficiently
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

# Create a ZIP file
current_time = datetime.now()
timestr_fname = current_time.strftime("%Y%m%d_%H%M")
zip_filename = f'build/deploypack-{timestr_fname}.zip'

print("Creating deploy pack with products: {}".format(", ".join(product_list)))
with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
    # Dictionary to store file hashes
    file_hashes = {}

    # Add each file to the ZIP and compute its hash
    for local_file in deploy_file_list:
        # Remove the src from the source files
        zip_path = local_file.replace("src/", "")

        # Verify file exists
        if not os.path.exists(local_file):
            print(f"Warning: File '{local_file}' not found.")
            continue
        # Compute SHA-256 hash
        file_hash = compute_sha256(local_file)
        file_hashes[zip_path] = file_hash
        # Add file to ZIP with the specified path
        zipf.write(local_file, zip_path)

    commit_id = subprocess.check_output(shlex.split('git log -1 --pretty=format:"%H"'))

    # Create a file with hashes on the fly
    hash_file_content = "\n".join(f"{hash}: {path}" for path, hash in file_hashes.items())
    hash_file_content = hash_file_content.encode('utf-8')  # Encode to bytes

    # Write the hash file directly to the ZIP
    zipf.writestr("hashes.txt", hash_file_content)
    zipf.writestr("commit_id.txt", commit_id)

print(f'Deploy pack file: {zip_filename}')

