import os
import sqlite3
import re
import time

from permissions import get_folder_owner, get_all_principal_permission

# Regex pattern for folder names
FOLDER_PATTERN = re.compile(r'^\d{6}-[a-zA-Z0-9 _\-!@#$%^&*()]+$')

# Function to add a job entry
def add_job(connection, root_folder, job_code, job_year, job_name):

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

    try:
        cursor = connection.cursor()
        for principal, permission_type, inheritance_type, source, owner in permissions:
            cursor.execute('''
                           INSERT INTO Permissions (Folder_Content_ID, Principal, Permission_Type, Inheritance_Type, Inheritance_Source)
                           VALUES (?, ?, ?, ?, ?)
                           ''', (folder_content_id, principal, permission_type, inheritance_type, source))
    except Exception as e:
        print(f"Error adding permissions for content ID {folder_content_id}: {e}")

#Function to process job folders
def process_job_folders(root_jobs_folder):

    with sqlite3.connect('C:\\Program Files\\DB Browser for SQLite\\TLC_folderpermission.db') as connection:

        for job_folder in os.listdir(root_jobs_folder):
            job_path = os.path.join(root_jobs_folder, job_folder)


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

    with sqlite3.connect('C:\\Users\\christopher.votoe\\PycharmProjects\\file_Permissions\\Database\\TLC_folderpermission.db') as connection:
        cursor = connection.cursor()
        cursor.execute('''SELECT ID,Job_Code, Job_Name
                          FROM Job
                          WHERE Job_Year = ?''', (year,))

        result = cursor.fetchall()

        if not result:
            print("No data found for the given year.")
            return []

        return [(ID, f"{Job_Code}-{Job_Name}") for ID, Job_Code, Job_Name in result]


# Query folder content info
def query_folder_content_info(job_id):
    with sqlite3.connect('C:\\Users\\christopher.votoe\\PycharmProjects\\file_Permissions\\Database\\TLC_folderpermission.db') as connection:
        cursor = connection.cursor()
        cursor.execute('''SELECT f.ID,f.Folder_Owner, f.Parent_Folder,f.Folder_Path,f.Folder_Date_Modified
                          FROM Folder_Contents f
                          WHERE f.Job_ID = ?
                       ''', (job_id,))

        result = cursor.fetchall()

        if not result:
            print("No folder content found for the given year.")
            return []


        return [
            (folder_id, parent_folder, folder_owner, folder_path,folder_date_modified)
            for folder_id, folder_owner, parent_folder, folder_path, folder_date_modified in result
        ]

def query_folder_content_folder_path(folder_id):
    with sqlite3.connect('C:\\Users\\christopher.votoe\\PycharmProjects\\file_Permissions\\Database\\TLC_folderpermission.db') as connection:
        cursor = connection.cursor()
        cursor.execute('''SELECT f.Folder_Path,f.Folder_Date_Modified
                          FROM Folder_Contents f
                          WHERE f.ID = ?
                       ''', (folder_id,))

        result = cursor.fetchall()

        if not result:
            print("No folder content found for the given year.")
            return []


        return [
            (folder_path, folder_date_modified)
            for folder_path, folder_date_modified in result
        ]


def query_permissions_info(folder_id):

    with sqlite3.connect('C:\\Users\\christopher.votoe\\PycharmProjects\\file_Permissions\\Database\\TLC_folderpermission.db') as connection:
        cursor = connection.cursor()
        cursor.execute('''SELECT p.Principal, p.Permission_Type, p.Inheritance_Type, p.Inheritance_Source
                          FROM Permissions p
                          WHERE p.Folder_Content_ID = ?

                       ''', (folder_id,))


        result = cursor.fetchall()


        if not result:
            print("No permissions found for the given year.")
            return []

        # Process and return results
        return [
            (Principal,Permission_Type,Inheritance_Type,Inheritance_Source) for Principal, Permission_Type, Inheritance_Type, Inheritance_Source in result
        ]

def delete_folder(folder_path):
    try:
        with sqlite3.connect('C:\\Users\\christopher.votoe\\PycharmProjects\\file_Permissions\\Database\\TLC_folderpermission.db') as connection:
            cursor = connection.cursor()
            cursor.execute("""
                           DELETE
                           FROM Folder_Contents
                           WHERE Folder_Path = ?
                           """, (folder_path,))


            connection.commit()

            print(f"Folder at path '{folder_path}' successfully deleted from the database.")
    except sqlite3.Error as e:
        print(f"An error occurred while deleting folder '{folder_path}': {e}")

def update_permissions(folder_path,new_folder_permissions,filesystem_date_modified):
    try:
        with sqlite3.connect('C:\\Users\\christopher.votoe\\PycharmProjects\\file_Permissions\\Database\\TLC_folderpermission.db') as connection:
            cursor = connection.cursor()

            cursor.execute(""" UPDATE Folder_Contents
                               SET Folder_Date_Modified = ?
                               WHERE Folder_Path = ?
                                """, (filesystem_date_modified,folder_path,))

            cursor.execute(""" SELECT ID FROM Folder_Contents WHERE Folder_Path = ?
                           
                           """,(folder_path,))

            folder_content_id=cursor.fetchone()

            if not folder_content_id:
                print("No folder content found for the given year.")
                return False
            else:
                folder_id=folder_content_id[0]
                #print(f"{folder_id}")

            cursor.execute("""DELETE FROM Permissions WHERE Folder_Content_ID = ?""",(folder_id,))
            #print("I'm here")

            for principal, permission_type, inheritance_type, inheritance_source, folder_owner in new_folder_permissions:
                #print(f"{principal} + {permission_type} + {inheritance_type} + {inheritance_source} + {folder_owner}")
                cursor.execute('''
                               INSERT INTO Permissions (Folder_Content_ID, Principal, Permission_Type, Inheritance_Type,
                                                        Inheritance_Source)
                               VALUES (?, ?, ?, ?, ?)
                               ''', (folder_id, principal, permission_type, inheritance_type, inheritance_source))

            connection.commit()
            print(f"Permissions for folder '{folder_path}' updated successfully.")
            return True

    except sqlite3.Error as e:
        print(f"An error occurred while deleting folder '{folder_path}': {e}")


#process_job_folders("L:\\2021-Jobs")









