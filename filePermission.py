import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import win32security
import win32con
import os
import ntsecuritycon as nt
import pathlib as path
import pyodbc as db
from dotenv import load_dotenv
import time
import datetime


PERMISSION_HIERARCH ={
    "Full Control": nt.FILE_ALL_ACCESS,
    "Modify": (nt.FILE_GENERIC_EXECUTE| nt.FILE_DELETE_CHILD| nt.FILE_GENERIC_READ | nt.FILE_GENERIC_WRITE ),
    "Read & Execute": nt.FILE_GENERIC_READ | nt.FILE_GENERIC_EXECUTE,
    "Write": nt.FILE_GENERIC_WRITE,
    "Read": nt.FILE_GENERIC_READ,
}

#works
def connect_db():
    try:
        load_dotenv()
        db_connection = db.connect('DRIVER={SQL Server};' + f'SERVER={os.getenv("DATABASE_SERVER")};'
                                                           f'DATABASE={os.getenv("DATABASE_NAME")};'
                                                           f'UID={os.getenv("DATABASE_USERNAME")};'
                                                           f'PWD={os.getenv("DATABASE_PASSWORD")};')

        return db_connection
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

#dbo.UU_PCA_Projects
def get_project_info(root_path, db_connection):
    try:
        folder_name = os.path.basename(root_path)
        project_number = folder_name.split('-')[0]

        cursor = db_connection.cursor()
        cursor.execute("""
               SELECT TOP (1) 
               p.[Project_Number], 
               p.[Project_Name], 
               e.[emp_name],
               d.[D_sname],
               d.[D_adm_name]
               FROM [dbo].[UU_PCA_Projects] p
               LEFT JOIN [dbo].[UU_Emps_All] e ON p.[Project_PM_Number] = e.[emp_code]
               LEFT JOIN [dbo].[UU_Divisions] d ON e.[org_code] = d.[Div_Code]
               WHERE [Project_Number] = ?
           """, (project_number,))

        result = cursor.fetchall()
        
        if result:
                db_connection.close()
        else:
            print(f"No project found with number: {project_number}")
                
        return result

    except Exception as e:
        print(f"Error in get_project_info: {e}")
        return None

#Evaluates the mask and determines the permission for each category.
def determine_hierarch(mask):
    #print(f"Debug: Determining permission for mask: {hex(mask)}")

    # Check Full Control first
    if mask == PERMISSION_HIERARCH["Full Control"]:

        return "Full Control"

    # Check Modify
    modify_mask = PERMISSION_HIERARCH["Modify"]
    if (mask == modify_mask) or (mask == 0x1301bf):

        return "Modify"


    # Check Read & Execute
    read_execute_mask = PERMISSION_HIERARCH["Read & Execute"]
    if (mask & read_execute_mask) == read_execute_mask:

        return "Read & Execute"

    # If no standard permissions
    specific = []

    for permission_type in ["Read", "Write", "Execute", "Delete"]:
        match permission_type:
            case "Read":
                if mask & nt.FILE_GENERIC_READ == nt.FILE_GENERIC_READ:
                    specific.append("Read")
            case "Write":
                if mask & nt.FILE_GENERIC_WRITE == nt.FILE_GENERIC_WRITE:
                    specific.append("Write")
            case "Execute":
                if mask & nt.FILE_GENERIC_EXECUTE == nt.FILE_GENERIC_EXECUTE:
                    specific.append("Execute")
            case "Delete":
                if mask & nt.FILE_DELETE_CHILD == nt.FILE_DELETE_CHILD:
                    specific.append("Delete")

    permission = " + ".join(specific) if specific else "Special"

    return permission

#List the permission for the provided folder path
def get_folder_permission(file_path):
    try:
        security_reader  = win32security.GetFileSecurity(file_path,win32security.DACL_SECURITY_INFORMATION)
        dacl = security_reader.GetSecurityDescriptorDacl()
        if dacl is None:
            return [("Error", "No DACL found", "")]

        security_permission = []

        #Loop through Access Control Entry, -List of who and what they have permissions to.
        for i in range(dacl.GetAceCount()):
            ace       = dacl.GetAce(i)
            ace_flags = ace[0][1]
            mask      = ace[1] #Shows if read,write...
            sid       = ace[2] #User in that row

            # SID is DOMAIN\User
            try:
                user, domain, _ = win32security.LookupAccountSid(None, sid)
                account = f"{domain}\\{user}"
            except win32security.error:
                account = f"Unknown SID: {sid}"
            # categorize mask
            perms = determine_hierarch(mask)

            permission = "".join(perms)

            # Checks inherited or None
            if ace_flags & win32security.INHERITED_ACE:
                source = "Inherited from above"
            else:
                source = "None"

            security_permission.append((account, permission, source))

        return security_permission

    except Exception as e:
        return [("Error", str(e), "")]

def get_all_folder_permission(root_path):
    folder_permission = {}

    for dirpath, dirnames, _ in os.walk(root_path, topdown=True):
        try:
            permissions = get_folder_permission(dirpath)
            relative_path = path.Path(dirpath).relative_to(root_path)
            folder_permission[str(relative_path)] = permissions

        except Exception as e:
            print(f"Error processing {dirpath}: {e}")

    return folder_permission

#Prints name, permission and inheritance
def print_all_folder_permission(root_path, progress_callback =None):
    start = time.time()
    folder_permission_data = get_all_folder_permission(root_path)

    #Allows me to save the report to their downloads with a timestamp
    try:
        downloads_dir = os.path.join(os.getenv("USERPROFILE") or os.getenv("HOME"), "Downloads")
        timestamp=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        report_filename = os.path.join(downloads_dir, f"permissions_report_{timestamp}.txt")
    except Exception as e:
        print(f"Error: {e}")

    with open(report_filename, 'w') as f:
        f.write(f"Below are all permission for all folders in: {root_path}\n")
        f.write("-" * 173 + "\n")

        root_permissions = get_folder_permission(root_path)
        f.write(f"\nRoot Folder: {root_path}\n")
        f.write("-" * 173 + "\n")
        f.write(f"{'User/Group':40} {'Permission':25} {'Source'}\n")
        f.write("-" * 173 + "\n")

        try:
            for user, perm, src in root_permissions:
                f.write(f"{user:40} {perm:25} {src}\n")
            f.write("-" * 173 + "\n")

            # Shows the number of folders for progress bar GUI
            num_folders = len(folder_permission_data)
            i = 0

            for folder_path, permissions in folder_permission_data.items():
                i += 1
                f.write(f"\nSubfolder: {root_path}\\{folder_path}\n")
                f.write("-" * 173 + "\n")
                f.write(f"{'User/Group':40} {'Permission':25} {'Source'}\n")
                f.write("-" * 173 + "\n")

                for user, perm, src in permissions:
                    f.write(f"{user:40} {perm:25} {src}\n")
                f.write("-" * 173 + "\n")
        except Exception as e:
            print(f"An error occurred: {e}")


    if progress_callback:
        progress_callback(i + 1, num_folders)

    end = time.time()
    total_time = end - start
    print(f"Results have been written to {report_filename}")

    #Opens the file after saving
    try:
        os.startfile(report_filename)
    except Exception as e:
        print(f"Error: {e}")

    return total_time, report_filename

def GUI():
    #Updates progress bar
    def update_progress(current, total):

        progress_value = int((current / total) * 100)
        progress_bar['value'] = progress_value
        root.update_idletasks()


    def handle_submit():
        file_path_value = file_path.get().strip()

        if os.path.exists(file_path_value):
            progress_bar['value'] = 0
            print("Processing...")

            # Disable the submitted/browse button to prevent multiple submissions
            file_submit_button.config(state=tk.DISABLED)
            browse_button.config(state=tk.DISABLED)

            for i in range(5):
                progress_bar.step(10)
                root.update_idletasks()
                time.sleep(0.05)


            try:
                handle_project_info()
                # Generate folder permissions report
                total_time, report_filename = print_all_folder_permission(file_path_value, update_progress)
                # Update the file location label with the generated file's path
                location_label.config(text=f"File saved at: {report_filename}", foreground="green")

                # Open the generated text file
                os.startfile(report_filename)
            except Exception as e:
                location_label.config(text=f"An error occurred: {e}")
                print(f"Error during file generation or project info retrieval: {e}")

            # Re-enable the submit button
            file_submit_button.config(state=tk.NORMAL)
            browse_button.config(state=tk.NORMAL)
        else:
            location_label.config(text="Error: Invalid folder path!")
            print("Error: Path does not exist.")

    #Lets user browse for folder along with pasting the path
    def allow_folder_browse():
        sel_direct = filedialog.askdirectory()
        if sel_direct:
            file_path.set(sel_direct)

    #Populates the listbox with the project information for the database
    def handle_project_info():
        file_path_value = file_path.get().strip()
        if os.path.exists(file_path_value):
            # Clear previous entries
            project_info.delete(0, tk.END)

            db_connection = connect_db()
            project_details = get_project_info(file_path_value,db_connection)
            if project_details:
                for row in project_details:
                    project_info.insert(tk.END, f"Project Number: {row[0]}")
                    project_info.insert(tk.END, f"Project Name: {row[1]}")
                    project_info.insert(tk.END, f"Project Manager: {row[2]}")
                    project_info.insert(tk.END, f"OU: {row[3]}")
                    project_info.insert(tk.END, f"OU Project Admin: {row[4]}")
            else:
                project_info.insert(tk.END, "No project details found.")
        else:
            print("Error: Path does not exist.")

    root = tk.Tk()
    root.title("Folder Permissions GUI")
    #Window
    root.geometry("800x650")
    #root.configure(background="light gray")

    style = ttk.Style()
    style.configure("BW.TLabel", font=("Arial", 15))


    #Folder Path
    file_path_label = ttk.Label(root, text="Enter Folder Path:", style="BW.TLabel")
    file_path_label.pack(pady=10)

    file_path = tk.StringVar()
    file_path_entry = ttk.Entry(root, textvariable=file_path, font=("Arial", 15), width=50)
    file_path_entry.pack(pady=5)

    # Frame to have buttons on the same line
    same_line_button_frame = ttk.Frame(root)
    same_line_button_frame.pack(pady=10)

    #Browse
    browse_button = ttk.Button(same_line_button_frame, text="Browse", command=allow_folder_browse,)
    browse_button.pack(side = "left", padx=5)

    #Submit Button
    file_submit_button = ttk.Button(same_line_button_frame, text="Submit", command=handle_submit)
    file_submit_button.pack(side = "left",padx=10)


    #List of Project Information
    label = ttk.Label(root, text="Project Details", font=("Arial", 15),style="BW.TLabel")
    label.pack(pady=10)
    #handle_project_info()
    project_info = tk.Listbox(root, font=("Arial", 12), width=60, height=5)
    project_info.pack(pady=10)

    same_line_progress_frame = ttk.Frame(root)
    same_line_progress_frame.pack(pady=5)

    # Progress Bar and Label
    progress_label = ttk.Label(same_line_progress_frame, text="Progress:",font = ('Arial', 15))
    progress_label.pack(side = 'left',padx=10)
    progress_bar = ttk.Progressbar(same_line_progress_frame, length=300, mode="determinate")
    progress_bar.pack(padx=10,pady=30)

    # File Location Label
    location_label_top = ttk.Label(root, text="Location of File Saved:", style="BW.TLabel",wraplength=850)
    location_label_top.pack(pady=10)
    location_label = ttk.Label(root, text="....", style="BW.TLabel",wraplength=850)
    location_label.pack(pady=10)

    root.mainloop()


#RUN THE SCRIPT
if __name__ == "__main__":
    GUI()