from ftplib import FTP
import os
import zipfile


save_dir = 'data/shape-files/state/2023'
ftp_dir = 'geo/tiger/TIGER2023/STATE/'

ftp = FTP('ftp2.census.gov')
ftp.login(user='anonymous', passwd='')

ftp.cwd(ftp_dir)

# Ensure the target directory exists
os.makedirs(save_dir, exist_ok=True)

# List all files in the current directory
files = ftp.nlst()

# Download each file
for file in files:
    local_filename = os.path.join(save_dir, file)
    with open(local_filename, 'wb') as f:
        ftp.retrbinary(f'RETR {file}', f.write)

# Extract each downloaded zip file and delete the zip file
for file in files:
    local_filename = os.path.join(save_dir, file)
    with zipfile.ZipFile(local_filename, 'r') as zip_ref:
        zip_ref.extractall(save_dir)
    os.remove(local_filename)

ftp.quit()

