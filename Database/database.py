# import os
# import sqlite3
# import re
# import time
#
# from permissions import get_folder_owner, get_all_principal_permission
#
# # Database connection
# # connection = sqlite3.connect('C:\\Program Files\\DB Browser for SQLite\\TLC_folderpermission.db')
# # cursor = connection.cursor()
#
# #Function to add a job entry
#
#
# FOLDER_PATTERN = re.compile(r'^\d{6}-[a-zA-Z0-9 _\-!@#$%^&*()]+$')
#
#
# def add_job(root_folder, job_code, job_year, job_name):
#     try:
#         cursor.execute('''
#                        INSERT
#                        OR IGNORE INTO Job (Root_Folder, Job_Code, Job_Year, Job_Name)
#         VALUES (?, ?, ?, ?)
#                        ''', (root_folder, job_code, job_year, job_name))
#         return cursor.lastrowid
#     except Exception as e:
#         print(f"Error adding job {job_code}: {e}")
#         return None
#
#
# # Function to add folder content
# def add_folder_content(job_id, folder_path, folder_owner,folder_date_modified,parent_folder_id = None):
#     try:
#         cursor.execute('''
#                        INSERT INTO Folder_Contents (Job_ID, Folder_Path, Folder_Owner,Folder_Date_Modified,Parent_Folder)
#
#                        VALUES (?, ?, ?, ?, ?)
#                        ''', (job_id, folder_path, folder_owner,folder_date_modified,parent_folder_id
# ))
#         return cursor.lastrowid
#     except Exception as e:
#         print(f"Error adding folder content {folder_path}: {e}")
#         return None
#
#
# # Function to add permissions
# def add_permissions(folder_content_id, permissions):
#     try:
#         for principal, permission_type, inheritance_type, source, owner in permissions:
#             cursor.execute('''
#                            INSERT INTO Permissions (Folder_Content_ID, Principal, Permission_Type, Inheritance_Type,
#                                                     Inheritance_Source)
#                            VALUES (?, ?, ?, ?, ?)
#                            ''', (folder_content_id, principal, permission_type, source, inheritance_type))
#     except Exception as e:
#         print(f"Error adding permissions for content ID {folder_content_id}: {e}")
#
#
# # Main script to process Job folders
# def process_job_folders(root_jobs_folder):
#
#     # Step 1: Get top-level folders (treated as Jobs)
#     for job_folder in os.listdir(root_jobs_folder):
#         job_path = os.path.join(root_jobs_folder, job_folder)
#
#         # Ensure it's a folder and matches the required pattern
#         if not os.path.isdir(job_path):
#             continue
#
#         if not FOLDER_PATTERN.match(job_folder):
#             # Skip folders that do not match the pattern
#             print(f"Skipping folder '{job_folder}' as it does not match the pattern.")
#             continue
#
#         print(f"Processing Job Folder: {job_path}")
#
#         # Extract the job code and name
#         job_code, job_name = job_folder.split("-", 1)  # Split by "-" into code and name
#         job_year = int("20"+job_folder[1:3])
#         #print(f"job year {job_year}")
#
#         # Add the job to the Job tabless
#         job_id = add_job(job_path, job_code, job_year, job_name)
#
#         if not job_id:
#             print(f"Error adding Job Folder: {job_folder}. Skipping.")
#             continue
#
#         # Step 2: Traverse deeper into the folder hierarchy
#         folder_ids = {}
#         for dirpath, _, _ in os.walk(job_path):
#             print(f"Processing folder: {dirpath}")
#
#             # Get folder owner
#             folder_owner = get_folder_owner(dirpath)
#
#             try:
#                 timestamp = os.path.getmtime(dirpath)
#                 last_modified_date = time.strftime('%Y-%m-%d %H:%M:%S',
#                                                    time.localtime(timestamp))  # Convert to readable format
#             except Exception as e:
#                 print(f"Error while retrieving last modified date for {dirpath}: {e}")
#                 last_modified_date = "Unknown"
#
#             parent_path = os.path.dirname(dirpath)  # Get the parent folder
#             parent_folder_id = folder_ids.get(parent_path)  # Lookup ID of the parent in our local tracking dictionary
#
#             # Add folder content to the databases
#             folder_content_id = add_folder_content(job_id, dirpath, folder_owner,last_modified_date,parent_folder_id)
#
#             # Get and add permissions if folder content was added
#             if folder_content_id:
#                 folder_ids[dirpath] = folder_content_id
#                 permissions = get_all_principal_permission(dirpath)
#                 add_permissions(folder_content_id, permissions)
#
# def query_job_info(year):
#     connection = sqlite3.connect('C:\\Program Files\\DB Browser for SQLite\\TLC_folderpermission.db')
#     cursor = connection.cursor()
#     cursor.execute('''SELECT Job_Code, Job_Name
#                       FROM Job
#                       WHERE Job_Year = ?''', (year,))
#     connection.close()
#     return cursor.fetchall()
#
# def query_folder_content_info(year):
#     connection = sqlite3.connect('C:\\Program Files\\DB Browser for SQLite\\TLC_folderpermission.db')
#     cursor = connection.cursor()
#     cursor.execute('''SELECT Folder_Owner,Parent_Folder
#                       FROM Job j
#                       LEFT JOIN Folder_Contents f
#                        ON j.ID = f.Job_ID
#                        WHERE j.Job_Year = ?
#                         ORDER BY f.ID ASC
#                       LIMIT 1000''', (year,))
#     connection.close()
#     return cursor.fetchall()
#
# def query_Permissions_info(year):
#     connection = sqlite3.connect('C:\\Program Files\\DB Browser for SQLite\\TLC_folderpermission.db')
#     cursor = connection.cursor()
#     cursor.execute('''SELECT Principal, Permission_Type, Inheritance_Type, Inheritance_Source
#     FROM Job j
#         LEFT JOIN Folder_Contents f on j.ID = f.Job_ID
#         LEFT JOIN Permissions p on f.ID = p.Folder_Content_ID
#         WHERE j.Job_Year = ?
#         ORDER BY p.ID ASC
#         LIMIT 1000
#     ''', (year,)
#     )
#     connection.close()
#     return cursor.fetchall()
#
#
#
#
# root_jobs_folder = "L:\\2023-Jobs"
#
#
# #process_job_folders(root_jobs_folder)
# # test = query_Permissions_info(2024)
# #
# # for x in test:
# #     print(x)
#
#
# # def clear_tables():
# #     try:
# #         # Disable foreign key checks temporarily
# #         cursor.execute('PRAGMA foreign_keys = OFF;')
# #
# #         # Clear data from all tables
# #         cursor.execute('DELETE FROM Permissions;')  # Clear the Permissions table
# #         cursor.execute('DELETE FROM Folder_Contents;')  # Clear the Folder_Contents table
# #         cursor.execute('DELETE FROM Job;')  # Clear the Job table
# #
# #         # OPTIONAL: Reset auto-increment counters for each table
# #         cursor.execute('DELETE FROM sqlite_sequence WHERE name = "Permissions";')
# #         cursor.execute('DELETE FROM sqlite_sequence WHERE name = "Folder_Contents";')
# #         cursor.execute('DELETE FROM sqlite_sequence WHERE name = "Job";')
# #
# #         # Re-enable foreign key checks
# #         cursor.execute('PRAGMA foreign_keys = ON;')
# #
# #         print("All data has been cleared from the tables.")
# #     except Exception as e:
# #         print(f"Error clearing table data: {e}")
#
#
# # Call the function to clear data
#
#
# # Commit and close the database connection
# # connection.commit()
# # connection.close()
#
# #print("All data has been uploaded to the database.")

import os
import sqlite3
import re
import time

from permissions import get_folder_owner, get_all_principal_permission

# Regex pattern for folder names
FOLDER_PATTERN = re.compile(r'^\d{6}-[a-zA-Z0-9 _\-!@#$%^&*()]+$')

# Function to add a job entry
def add_job(connection, root_folder, job_code, job_year, job_name):
    """Insert a job into the database."""
    try:
        cursor = connection.cursor()
        cursor.execute('''
                       INSERT OR IGNORE INTO Job (Root_Folder, Job_Code, Job_Year, Job_Name)
                       VALUES (?, ?, ?, ?)
                       ''', (root_folder, job_code, job_year, job_name))
        return cursor.lastrowid  # Return the ID of the newly added job
    except Exception as e:
        print(f"Error adding job {job_code}: {e}")
        return None

# Function to add folder content
def add_folder_content(connection, job_id, folder_path, folder_owner, folder_date_modified, parent_folder_id=None):
    """Insert folder content into the database."""
    try:
        cursor = connection.cursor()
        cursor.execute('''
                       INSERT INTO Folder_Contents (Job_ID, Folder_Path, Folder_Owner, Folder_Date_Modified, Parent_Folder)
                       VALUES (?, ?, ?, ?, ?)
                       ''', (job_id, folder_path, folder_owner, folder_date_modified, parent_folder_id))
        return cursor.lastrowid  # Return the ID of the newly added folder content
    except Exception as e:
        print(f"Error adding folder content {folder_path}: {e}")
        return None

# Function to add permissions
def add_permissions(connection, folder_content_id, permissions):
    """Insert permissions into the database."""
    try:
        cursor = connection.cursor()
        for principal, permission_type, inheritance_type, source, owner in permissions:
            cursor.execute('''
                           INSERT INTO Permissions (Folder_Content_ID, Principal, Permission_Type, Inheritance_Type, Inheritance_Source)
                           VALUES (?, ?, ?, ?, ?)
                           ''', (folder_content_id, principal, permission_type, inheritance_type, source))
    except Exception as e:
        print(f"Error adding permissions for content ID {folder_content_id}: {e}")

# Function to process job folders
def process_job_folders(root_jobs_folder):
    """Process the job folders and insert data into the database."""
    with sqlite3.connect('C:\\Program Files\\DB Browser for SQLite\\TLC_folderpermission.db') as connection:
        # Step 1: Get top-level folders (treated as Jobs)
        for job_folder in os.listdir(root_jobs_folder):
            job_path = os.path.join(root_jobs_folder, job_folder)

            # Ensure it's a folder and matches the required pattern
            if not os.path.isdir(job_path):
                continue

            if not FOLDER_PATTERN.match(job_folder):
                print(f"Skipping folder '{job_folder}' as it does not match the pattern.")
                continue

            print(f"Processing Job Folder: {job_path}")

            # Extract the job code and name
            job_code, job_name = job_folder.split("-", 1)
            job_year = int("20" + job_folder[1:3])

            # Add the job to the Job table
            job_id = add_job(connection, job_path, job_code, job_year, job_name)

            if not job_id:
                print(f"Error adding Job Folder: {job_folder}. Skipping.")
                continue

            # Step 2: Traverse deeper into the folder hierarchy
            folder_ids = {}
            for dirpath, _, _ in os.walk(job_path):
                print(f"Processing folder: {dirpath}")

                folder_owner = get_folder_owner(dirpath)

                try:
                    timestamp = os.path.getmtime(dirpath)
                    last_modified_date = time.strftime('%Y-%m-%d %H:%M:%S',
                                                       time.localtime(timestamp))
                except Exception as e:
                    print(f"Error retrieving last modified date for {dirpath}: {e}")
                    last_modified_date = "Unknown"

                parent_path = os.path.dirname(dirpath)
                parent_folder_id = folder_ids.get(parent_path)

                # Add folder content to the database
                folder_content_id = add_folder_content(
                    connection, job_id, dirpath, folder_owner, last_modified_date, parent_folder_id
                )

                # Add permissions if folder content was added
                if folder_content_id:
                    folder_ids[dirpath] = folder_content_id
                    permissions = get_all_principal_permission(dirpath)
                    add_permissions(connection, folder_content_id, permissions)

# Query job info
def query_job_info(year):
    """Query job info based on the year."""
    with sqlite3.connect('C:\\Program Files\\DB Browser for SQLite\\TLC_folderpermission.db') as connection:
        cursor = connection.cursor()
        cursor.execute('''SELECT Root_Folder
                          FROM Job
                          WHERE Job_Year = ?''', (year,))

        # Fetch all results at once
        result = cursor.fetchall()

        # Check if the result is empty
        if not result:
            print("No data found for the given year.")
            return []

        # Process and return results
        return [f"{Root_Folder}" for Root_Folder in result]


# Query folder content info
def query_folder_content_info(year):
    """Query folder content information."""
    with sqlite3.connect('C:\\Program Files\\DB Browser for SQLite\\TLC_folderpermission.db') as connection:
        cursor = connection.cursor()
        cursor.execute('''SELECT Folder_Owner, Parent_Folder,Folder_Path
                          FROM Job j
                                   LEFT JOIN Folder_Contents f
                                             ON j.ID = f.Job_ID
                          WHERE j.Job_Year = ?
                          
                            
                       ''', (year,))

        # Fetch all results at once
        result = cursor.fetchall()

        # Check if the result is empty
        if not result:
            print("No folder content found for the given year.")
            return []

        # Process and return results
        return [f"{folder_owner}-{parent_folder}-{Folder_Path}" for folder_owner, parent_folder,Folder_Path in result]


# Query permissions info
def query_permissions_info(year):
    """Query permissions info."""
    with sqlite3.connect('C:\\Program Files\\DB Browser for SQLite\\TLC_folderpermission.db') as connection:
        cursor = connection.cursor()
        cursor.execute('''SELECT Principal, Permission_Type, Inheritance_Type, Inheritance_Source
                          FROM Job j
                                   LEFT JOIN Folder_Contents f ON j.ID = f.Job_ID
                                   LEFT JOIN Permissions p ON f.ID = p.Folder_Content_ID
                          WHERE j.Job_Year = ?
                          ORDER BY p.ID ASC
                             
                       ''', (year,))

        # Fetch all results at once
        result = cursor.fetchall()

        # Check if the result is empty
        if not result:
            print("No permissions found for the given year.")
            return []

        # Process and return results
        return [f"{principal} {permission_type} {inheritance_type} {source}"
                for principal, permission_type, inheritance_type, source in result]

#
# test = query_permissions_info(2077)
# for x in test:
#     print(x)
#process_job_folders("L:\\2077-Jobs")