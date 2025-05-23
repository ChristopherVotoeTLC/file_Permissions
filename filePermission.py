from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QLineEdit, QPushButton,
    QLabel, QListWidget, QProgressBar, QWidget, QFileDialog, QShortcut, QHBoxLayout, QCheckBox
)
import qtawesome as qta
import sys
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

#Evaluates the mask and determines the permission
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

#List the permission for the provided folder path m
def get_folder_permission(file_path):
    try:
        security_reader  = win32security.GetFileSecurity(file_path,win32security.DACL_SECURITY_INFORMATION)
        dacl = security_reader.GetSecurityDescriptorDacl()
        if dacl is None:
            return [("Error", "No DACL found", "")]

        security_permission = []

        #Loop through Access Control Entry, -List of whom and what they have permissions to.
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

def get_user_permissions_only(file_path):
    try:
        # Retrieve the security descriptor for the given file
        security_reader = win32security.GetFileSecurity(file_path, win32security.DACL_SECURITY_INFORMATION)
        dacl = security_reader.GetSecurityDescriptorDacl()

        if dacl is None:
            return [("Error", "No DACL found", "")]

        user_permissions = []

        # Loop through all Access Control Entries (ACE)
        for i in range(dacl.GetAceCount()):
            ace = dacl.GetAce(i)
            ace_flags = ace[0][1]
            mask = ace[1]  # Access mask (permissions)
            sid = ace[2]  # Security Identifier (SID)

            # Check only for "User" principals
            principal_type = get_principal_type(sid)
            if principal_type == "User":  # Only process users
                try:
                    # Retrieve DOMAIN\USERNAME from SID
                    user, domain, _ = win32security.LookupAccountSid(None, sid)
                    account = f"{domain}\\{user}"
                except win32security.error:
                    account = f"Unknown SID: {sid}"

                # Determine categorized permissions based on mask
                perms = determine_hierarch(mask)
                permission = "".join(perms)

                # Check for inheritance flags
                if ace_flags & win32security.INHERITED_ACE:
                    source = "Inherited from above"
                else:
                    source = "None"

                # Append to user-specific permission results
                user_permissions.append((account, permission, source))

        return user_permissions

    except Exception as e:
        return [("Error", str(e), "")]

def get_principal_type(sid):
    try:
        _, _, account_type = win32security.LookupAccountSid(None, sid)
        if account_type == win32security.SidTypeUser:
            return "User"
        elif account_type == win32security.SidTypeGroup:
            return "Group"
        elif account_type == win32security.SidTypeWellKnownGroup:
            return "Well-Known Group"
        return "Other"
    except win32security.error:
        return "Unknown"


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


    num_folders = len(folder_permission_data)
    if progress_callback:
        progress_callback(0, num_folders)
    i = 0

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
                i+=1
                f.write(f"{user:40} {perm:25} {src}\n")
            f.write("-" * 173 + "\n")
            for folder_path, permissions in folder_permission_data.items():

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
        progress_callback(i , num_folders)

    end = time.time()
    total_time = end - start
    print(f"Results have been written to {report_filename}")

    #Opens the file after saving
    try:
        os.startfile(report_filename)
    except Exception as e:
        print(f"Error: {e}")

    return total_time, report_filename

class TestGUI(QMainWindow):
    class FolderPermissionWorker(QThread):
        progress_update = pyqtSignal(int)  # Signal for reporting progress
        task_completed = pyqtSignal(float, str)  # Signal for task completion (total time and report file)

        def __init__(self, root_path):
            super().__init__()
            self.root_path = root_path  # The root path for processing

        def run(self):
            def progress_callback(current, total):
                # Calculate the percentage progress
                if total > 0:
                    progress_percentage = int((current / total) * 100)
                    self.progress_update.emit(progress_percentage)

            # Call the function and process the folders
            total_time, report_file = print_all_folder_permission(self.root_path, progress_callback)

            # Emit the signal for task completion when done
            self.task_completed.emit(total_time, report_file)


    def __init__(self):
        super().__init__()
        self.start_gui()

    def start_gui(self):
        # Set up a window
        self.setWindowTitle("Folder Permissions GUI")
        self.setGeometry(100, 100, 700, 500)


        #Syling!!
        self.setStyleSheet("""
    /* Main Window */
    QMainWindow {
        background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #F5F5F5, stop:1 #4ca1af);
        color: #000000;  /* text color */
        font-family: "Roboto", sans-serif; /* not sure which this affects yet*/
        font-size: 18px;
    }

    /* Labels for headings*/
    QLabel {
        color: #000000;
        font-size: 18px;
        font-weight: bold;
        font-family: "Roboto", sans-serif;
        padding: 5px;
    }

    /* Input fields (QLineEdit) */
    QLineEdit {
        background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #F5F5F5, stop:1 #4ca1af);
        color: #00000; /*TEXT COLOR*/
        font-weight: bold;
        font-family: "Roboto", sans-serif;
        font-size : 15px;
        border: 1px solid #2c3e50;
        border-radius: 8px;
        padding: 5px;
    }
    QLineEdit:focus {
        border: 1px solid #3498db;  /* Focus color */
    }

    /* Buttons (QPushButton) */
    QPushButton {
        background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #F5F5F5, stop:1 #4ca1af);
        color: black;
        font-weight: bold;
        font-family: "Roboto", sans-serif;
        font-size : 15px;
        border: 1px solid #2c3e50;
        border-radius: 10px;
        padding: 7px 15px;
        
    }
    QPushButton:hover {
        background-color: #2980b9;  /* Hover effect */
    }
    QPushButton:pressed {
        background-color: #1c598b;  /* Pressed effect */
    }
    
    /*Checkbox*/
    QCheckBox {
    font-weight: bold;
        font-family: "Roboto", sans-serif;
        font-size : 15px;
    }

    /* Progress Bar */
    QProgressBar {
        text-align: center;
        color: black; /*text*/
        background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #F5F5F5, stop:1 #4ca1af);
        border: 1px solid #2c3e50;
        border-radius: 5px;
    }
    QProgressBar::chunk {
        background-color: #39c45f;  /* Fill color */
        border-radius: 5px;
    }

    /* List Widget */
    QListWidget {
        background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #F5F5F5, stop:1 #4ca1af);
        color: #000000; /*Input field text color*/
        border: 1px solid #2c3e50;
        border-radius: 5px;
        padding: 5px;
        font-weight: bold;
        font-family: "Roboto", sans-serif;
        font-size: 15px; /*affects text in list*/
    }
    QListWidget::item {
        padding: 5px;
        border: none;
    }
    QListWidget::item:hover {
        
    }
    QListWidget::item:selected {
        
        color: black;
    }

    /* QFileDialog (Browse File Dialog) */
    QFileDialog {
        background-color: #2c3e50;
        color: white;
    }
""")

        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Folder Path Input
        folder_path_label = QLabel("Enter Folder Path:")
        layout.addWidget(folder_path_label)

        # Allows items on the same line
        self.horizontal_layout = QHBoxLayout()
        layout.addLayout(self.horizontal_layout)

        #Input line with file path
        self.file_path_input = QLineEdit()
        self.horizontal_layout.addWidget(self.file_path_input)

        # Browse Button
        browse_button = QPushButton("Browse")
        browse_button.setIcon(qta.icon('fa5s.file-import'))
        browse_button.clicked.connect(self.browse_folder)
        self.horizontal_layout.addWidget(browse_button)

        # Submit Button and Progress Bar Layout
        submit_button = QPushButton("Search")
        submit_button.setIcon(qta.icon('fa5s.search'))
        submit_button.clicked.connect(self.handle_submit)
        self.horizontal_layout.addWidget(submit_button)

        #Inheritance Checkbox
        inheritance_checkbox = QCheckBox("Include Inherited Permissions (Will take longer to compute)")
        inheritance_checkbox.setChecked(False)
        layout.addWidget(inheritance_checkbox)

        show_groups_checkbox = QCheckBox("Include Groups")
        show_groups_checkbox.setChecked(True)
        layout.addWidget(show_groups_checkbox)

        show_individuals_checkbox = QCheckBox("Include Individuals")
        show_individuals_checkbox.setChecked(True)
        layout.addWidget(show_individuals_checkbox)

        # Project Details Sections
        project_details_label = QLabel("Project Details: (Ctrl + A to select all & Ctrl + C to copy)")
        layout.addWidget(project_details_label)

        self.project_info_list = QListWidget()
        self.project_info_list.setSelectionMode(QListWidget.ExtendedSelection)
        layout.addWidget(self.project_info_list)

        # Enable copy and select-all shortcuts
        copy_shortcut = QShortcut(QKeySequence("Ctrl+C"), self)
        copy_shortcut.activated.connect(self.copy_selected_items)

        select_all_shortcut = QShortcut(QKeySequence("Ctrl+A"), self)
        select_all_shortcut.activated.connect(self.select_all_items)



        #Label with file location
        self.file_location_label = QLabel("File Location:")
        layout.addWidget(self.file_location_label)
        self.file_path = QLineEdit()
        layout.addWidget(self.file_path)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0) #maybe get rid of
        layout.addWidget(self.progress_bar)

    # Used to open a folder directory when browse is clicked
    def browse_folder(self):
        selected_folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if selected_folder:
            self.file_path_input.setText(selected_folder)

    def handle_submit(self):
        file_path = self.file_path_input.text().strip()
        if not file_path or not os.path.exists(file_path):
            self.show_error_message("Invalid folder path.")
            return

        self.progress_bar.setValue(0)


        try:
            #db_connection = connect_db()
           # if db_connection:
                # Fetch and display project details
            self.progress_bar.setValue(15)
              #  project_info = get_project_info(file_path, db_connection)
               # self.display_project_info(project_info)

            # Start the worker thread
            self.worker = self.FolderPermissionWorker(file_path)
            self.worker.progress_update.connect(self.update_progress_bar)  # Connect progress updates
            self.worker.task_completed.connect(self.task_completed)  # Connect task completion
            self.worker.start()  # Start the worker thread

        except Exception as e:
            print(F"An error occurred: {e}")

    def display_project_info(self, project_info):
        self.project_info_list.clear() #Clears a listbox before starting
        if not project_info:
            self.project_info_list.addItem("No project found.")
            return

        for row in project_info:
            project_number = row[0]
            project_name = row[1]
            emp_name = row[2]
            division_name = row[3]
            division_admin = row[4]

        self.project_info_list.addItem(f"Project Number: {project_number}")
        self.project_info_list.addItem(f"Project Name: {project_name}")
        self.project_info_list.addItem(f"Employee Name: {emp_name}")
        self.project_info_list.addItem(f"Division Name: {division_name}")
        self.project_info_list.addItem(f"Division Admin: {division_admin}")

    def update_progress_bar(self, value):

        self.progress_bar.setValue(value)

    def task_completed(self, total_time, report_file):
        self.file_path.setText(report_file)
        print(f"Task completed in {total_time:.2f} seconds.")
        self.progress_bar.setValue(100)

    def copy_selected_items(self):

        selected_items = self.project_info_list.selectedItems()
        selected_text = "\n".join(item.text() for item in selected_items)
        QApplication.clipboard().setText(selected_text)

    def select_all_items(self):

        self.project_info_list.selectAll()


# Run the application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    test_window = TestGUI()
    test_window.show()
    sys.exit(app.exec())


