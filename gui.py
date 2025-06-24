import re
from datetime import datetime

from PyQt5.QtCore import QThread, pyqtSignal, Qt, QObject, QTimer
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QListWidget, QProgressBar, QFileDialog,
    QLineEdit, QShortcut, QPushButton, QCheckBox, QApplication, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QTableWidgetItem, QTableWidget, QHeaderView
)
import qtawesome as qta
import os
from permissions import (
    get_all_principal_permission,get_folder_owner
)
from Database.database import (
    query_job_info, query_folder_content_info, query_permissions_info, process_job_folders, delete_folder,
    add_folder_content,add_permissions,update_permissions
)
class PermissionLoaderWorker(QObject):
    finished = pyqtSignal(object)
    #progress = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, folder_id):
        super().__init__()
        self.folder_id = folder_id

    def run(self):
        try:
            permissions = query_permissions_info(self.folder_id)
            self.finished.emit(permissions)
        except Exception as e:
            self.error.emit(str(e))

class ProcessJobThread(QThread):
    finished = pyqtSignal()

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        # Run the long process in a separate thread
        process_job_folders(self.file_path)
        self.finished.emit()

class FolderExpansionWorker(QObject):
    finished = pyqtSignal(object)
    progress = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, job_id, folders, compare_fn):
        super().__init__()
        self.job_id = job_id
        self.folders = folders
        self.compare_fn = compare_fn

    def run(self):
        folder_map = {}
        try:
            total = len(self.folders)
            for idx, (folder_id, parent, owner, path, mod_date) in enumerate(self.folders):
                result = self.compare_fn(path, mod_date, self.job_id, parent)
                if result in ("DB up to date", "DB UPDATED"):
                    folder_map.setdefault(parent, []).append((folder_id, owner, path))
                self.progress.emit(int((idx + 1) / total * 100))
            self.finished.emit(folder_map)
        except Exception as e:
            self.error.emit(str(e))

class TestGUI(QMainWindow):

    def __init__(self):
        super().__init__()
        self.start_gui()
        self.reference_permissions = {}

    def start_gui(self):
        # Set up a window
        self.setWindowTitle("Folder Permissions GUI")
        # Adds the fullscreen/minimize/close in the top right of the gui
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
        self.setGeometry(20,26, 1800, 1000)

        # Styling!!
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

    QTreeWidget {
        background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #F5F5F5, stop:1 #4ca1af);
        color: #000000; /*Input field text color*/
        padding: 5px;
        font-weight: bold;
        font-family: "Roboto", sans-serif;
        font-size: 12px; 
    }
    /*Children branches such as each folder*/
    QTreeWidget::item:!has-children { 

        color: #00000;
        font-weight: Normal;
        font-family: "Roboto", sans-serif;
        font-size: 12px; 

    }

    QHeaderView {
        background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #F5F5F5, stop:1 #4ca1af);
        color: #000000; /*Input field text color*/
        font-weight: bold;
        font-family: "Roboto", sans-serif;
        font-size: 15px; 
    }
    QHeaderView::section {
        background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #F5F5F5, stop:1 #4ca1af);
        border: 1px solid #4ca1af;  
        padding: 2px;

    }
    QScrollBar:vertical {
        background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #F5F5F5, stop:1 #4ca1af);
        border: none;
    }
    QTableWidget {
        background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #F5F5F5, stop:1 #4ca1af);
        color: #000000; /*Input field text color*/
        font-weight: bold;
        font-family: "Roboto", sans-serif;
        font-size: 15px; 
    }
""")

        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Allows items on the same line
        self.horizontal_layout = QHBoxLayout()
        layout.addLayout(self.horizontal_layout)

        # Folder Path Input
        folder_path_label = QLabel("Choose Project Year Folder:")
        self.horizontal_layout.addWidget(folder_path_label)



        # Input line with a file path
        self.file_path_input = QLineEdit()
        self.horizontal_layout.addWidget(self.file_path_input)
        # _2077_button = QPushButton("2077")
        # #_2020_button.setIcon(qta.icon('fa5s.search'))
        # _2077_button.clicked.connect(lambda: self.handle_submit("2077"))
        # self.horizontal_layout.addWidget(_2077_button)
        #
        #
        # _2021_button = QPushButton("2021")
        # #_2021_button.setIcon(qta.icon('fa5s.search'))
        # _2021_button.clicked.connect(lambda: self.handle_submit("2021"))
        # self.horizontal_layout.addWidget(_2021_button)
        #
        # _2022_button = QPushButton("2022")
        # #_2022_button.setIcon(qta.icon('fa5s.search'))
        # _2022_button.clicked.connect(lambda: self.handle_submit("2022"))
        # self.horizontal_layout.addWidget(_2022_button)
        #
        # _2023_button = QPushButton("2023")
        # #_2023_button.setIcon(qta.icon('fa5s.search'))
        # _2023_button.clicked.connect(lambda: self.handle_submit("2023"))
        # self.horizontal_layout.addWidget(_2023_button)
        #
        # _2024_button = QPushButton("2024")
        # #_2024_button.setIcon(qta.icon('fa5s.search'))
        # _2024_button.clicked.connect(lambda: self.handle_submit("2024"))
        # self.horizontal_layout.addWidget(_2024_button)
        #
        # _2025_button = QPushButton("2025")
        # #_2025_button.setIcon(qta.icon('fa5s.search'))
        # _2025_button.clicked.connect(lambda: self.handle_submit("2025"))
        # self.horizontal_layout.addWidget(_2025_button)

        # self.display_all_perms = QCheckBox("Display All Permissions (Will take longer to compute)")
        # self.display_all_perms.setChecked(False)
        # self.display_all_perms.stateChanged.connect(self.toggle_display_all_permissions)
        # layout.addWidget(self.display_all_perms)



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

        # Inheritance Checkbox
        # self.inheritance_checkbox = QCheckBox("Include Inherited Permissions (Will take longer to compute)")
        # self.inheritance_checkbox.setChecked(False)
        # layout.addWidget(self.inheritance_checkbox)

        # self.show_groups_checkbox = QCheckBox("Include Groups")
        # self.show_groups_checkbox.setChecked(False)
        # layout.addWidget( self.show_groups_checkbox)

        # self.show_users_checkbox = QCheckBox("Only Users")
        # self.show_users_checkbox.setChecked(True)
        # layout.addWidget(self.show_users_checkbox)

        # Project Details Sections
        # project_details_label = QLabel("Project Details: (Ctrl + A to select all & Ctrl + C to copy)")
        # layout.addWidget(project_details_label)
        #
        # self.project_info_list = QListWidget()
        # self.project_info_list.setSelectionMode(QListWidget.ExtendedSelection)
        # layout.addWidget(self.project_info_list)
        #
        # # Enable copy and select-all shortcuts
        # copy_shortcut = QShortcut(QKeySequence("Ctrl+C"), self)
        # copy_shortcut.activated.connect(self.copy_selected_items)
        #
        # select_all_shortcut = QShortcut(QKeySequence("Ctrl+A"), self)
        # select_all_shortcut.activated.connect(self.select_all_items)

        # Tree widget for displaying folder structure and permissions
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Folder","Folder Owner"])

        self.inherited_permissions = {}

        self.tree_widget.setColumnWidth(0, 500)
        self.tree_widget.setColumnWidth(1, 200)
        # self.tree_widget.setColumnWidth(2, 275)
        # self.tree_widget.setColumnWidth(3, 200)
        # self.tree_widget.setColumnWidth(4, 450)
        # self.tree_widget.setColumnWidth(5, 250)
        layout.addWidget(self.tree_widget)

        self.tree_widget.itemExpanded.connect(self.on_tree_expand)
        self.tree_widget.itemClicked.connect(self.on_tree_item_clicked)

        self.permissions_table = QTableWidget()
        self.permissions_table.setColumnCount(4)
        self.permissions_table.setHorizontalHeaderLabels(["Principal", "Permission", "Inheritance Type", "Source"])
        self.permissions_table.horizontalHeader().setStretchLastSection(True)
        self.permissions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.permissions_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.permissions_table.setSortingEnabled(False)
        self.permissions_table.verticalHeader().setVisible(False)
        self.permissions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.permissions_table)

        # # Add a test item with a placeholder "Loading..." child
        # test_item = QTreeWidgetItem(["Sample Job", "Owner", "", "", "", ""])
        # test_item.setData(0, Qt.UserRole, {"type": "job", "id": 1})  # Example metadata
        # test_item.addChild(QTreeWidgetItem(["Loading..."]))
        # self.tree_widget.addTopLevelItem(test_item)
        #
        # folder_item = QTreeWidgetItem(["Sample Folder", "Owner", "", "", "", ""])
        # folder_item.setData(0, Qt.UserRole, {"type": "folder", "path": "/path/to/folder"})
        # folder_item.addChild(QTreeWidgetItem(["Loading..."]))
        # test_item.addChild(folder_item)

        search_layout = QHBoxLayout()

        # Search Tree input
        self.search_tree = QLineEdit()
        self.search_tree.setPlaceholderText("Enter search term...")
        search_layout.addWidget(self.search_tree)

        # Search button
        search_button = QPushButton("Search")
        search_button.setIcon(qta.icon('fa5s.search'))

        search_button.clicked.connect(self.search_tree_1)
        search_layout.addWidget(search_button)
        layout.addLayout(search_layout)

        # -----------------------------Got rid of to use only tree widget------------------------#
        # Label with file location
        # self.file_location_label = QLabel("File Location:")
        # layout.addWidget(self.file_location_label)
        # self.file_path = QLineEdit()
        # layout.addWidget(self.file_path)
        # --------------------------------------------------------------------------------------

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

    # def update_tree_widget(self, folder_permissions):
    #     self.tree_widget.clear()
    #
    #     # Dict to store which folders become children of other folders in the tree
    #     tree_data = {}
    #
    #     # Build the tree_data dictionary
    #     for folder, permissions in folder_permissions.items():
    #         parts = folder.split("\\")  # splits folder_path
    #         first_part = parts[0]  # This is the top branch
    #
    #         # If it doesn't exist in tree_data, add it
    #         if first_part not in tree_data:
    #             tree_data[first_part] = {"permissions": [], "subfolders": {}}
    #             # Permission holds rules while subfolder hold child branches
    #
    #         current_level = tree_data[first_part]
    #         for part in parts[1:]:
    #             if part not in current_level["subfolders"]:
    #                 current_level["subfolders"][part] = {"permissions": [], "subfolders": {}}
    #
    #             # moves to branch with subfolder and inserts it
    #             current_level = current_level["subfolders"][part]
    #
    #         # Once all subfolders are done, add the permissions
    #         current_level["permissions"].extend(permissions)
    #
    #     def add_items(parent_item, folder_data):
    #         # List that will hold all the branches, starts with just the parent branch and its data
    #         holder_list = [(parent_item, folder_data)]
    #
    #         while holder_list:
    #             current_parent, current_data = holder_list.pop()
    #
    #             # Iterate through folders at the current branch
    #             for folder_name, folder_details in current_data.items():
    #                 if folder_name == "permissions":
    #                     continue
    #
    #                 # Extract owner for this branch
    #                 branch_owner = folder_details["permissions"][0][4] if folder_details["permissions"] else "No Owner"
    #                 # 2025 folder with jobs starting in 225*** gave no owner but had owner?? test on 2024 folder
    #
    #                 # Create a new tree branch and display the owner once on this branch
    #                 folder_item = QTreeWidgetItem([folder_name, "", "", "", "", f"{branch_owner}"])
    #
    #                 current_parent.addChild(folder_item)
    #
    #                 # Add permissions for this branch
    #                 for user1, perm1, source1, type1, _ in folder_details["permissions"]:
    #                     permission_item1 = QTreeWidgetItem(
    #                         ["", f"{user1}", f"     {perm1}", f"{source1}", f"{type1}", ""]
    #                     )
    #                     folder_item.addChild(permission_item1)
    #
    #                 # Adds the branch to the hold list if the folder has subfolders
    #                 holder_list.append((folder_item, folder_details["subfolders"]))
    #
    #     # Starts filling the tree widget
    #     for top_folder, details, in tree_data.items():
    #         # Extract the owner of the top-level folder
    #         top_owner = details["permissions"][0][4] if details["permissions"] else "No Owner"
    #
    #         #
    #         top_item = QTreeWidgetItem([top_folder, "", "", "", "", top_owner])
    #         self.tree_widget.addTopLevelItem(top_item)
    #
    #         # Add permissions for the top-level
    #         for user, perm, source, type, _ in details["permissions"]:
    #             permission_item = QTreeWidgetItem(
    #                 ["", f"{user}", f"     {perm}", f"{source}", f"{type}", ""]
    #             )
    #             top_item.addChild(permission_item)
    #
    #         # Add subfolders
    #         add_items(top_item, details["subfolders"])
    #
    #     self.progress_bar.setValue(100)

    def search_tree_1(self):
        search_term = self.search_tree.text().strip()
        if not search_term:
            self.show_error_message("Please enter a search term.")
            return

        search_term = search_term.lower()

        self.highlight_searched_item(self.tree_widget, search_term)

    def highlight_searched_item(self, tree_widget, search_term):

        for i in range(tree_widget.topLevelItemCount()):
            top_item = tree_widget.topLevelItem(i)
            self.search_items(top_item, search_term)

    def search_items(self, item, search_term):

        item.setBackground(0, Qt.transparent)
        item.setBackground(1, Qt.transparent)
        item.setBackground(2, Qt.transparent)

        found = False



        for col in range(item.columnCount()):
            if search_term in item.text(col).lower():
                # Highlight the matching item
                item.setBackground(col, Qt.yellow)
                found = True
        if found:
            self.tree_widget.scrollToItem(item)

        for i in range(item.childCount()):
            child = item.child(i)
            self.search_items(child, search_term)

    def clear_tree_selection(self):

        for i in range(self.tree_widget.topLevelItemCount()):
            top_item = self.tree_widget.topLevelItem(i)
            self.clear_items(top_item)

    def clear_items(self, item):

        for col in range(item.columnCount()):
            item.setBackground(col, Qt.transparent)

        # Recursively clear background color for all children
        for i in range(item.childCount()):
            child = item.child(i)
            self.clear_items(child)

    def browse_folder(self):
        selected_folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if selected_folder:
            self.file_path_input.setText(selected_folder)


    def process_done(self):
        error = QTreeWidgetItem(["", "", "", "", "", ""])
        error.setText(0, "Job  in database")
        self.tree_widget.addTopLevelItem(error)

    def handle_submit(self):
        try:
            file_path = self.file_path_input.text().strip()
            pattern = r"L:/\d{4}-Jobs.*"
            if re.fullmatch(pattern, file_path):
                year = file_path.split("/")[1][:4]
                print(f"Year received: {year}")
                job_info = query_job_info(year)
                if not job_info: #The year is not in the DB, process it into DB BUT will take some time depending on size
                    self.tree_widget.clear()
                    print("Job not in database")
                    error = QTreeWidgetItem(["", "", "", "", "", ""])
                    error.setText(0, "Job not in database")
                    error.setText(1, "Please wait while the job is processed")
                    error.setText(2, "This may take a While")
                    error.setText(3, "If the job is still not processed, please contact the administrator")
                    error.setText(4, "If the job is processed, please try again")
                    error.setText(5, "")
                    self.tree_widget.addTopLevelItem(error)

                    self.tree_widget.repaint()
                    QApplication.processEvents()

                    self.thread = ProcessJobThread(file_path)
                    self.thread.finished.connect(self.process_done)
                    self.thread.start()
                    return

                self.tree_widget.clear()
                self.populate_jobs(job_info)
            else:
                print("Year not found or file path is invalid.")

        except Exception as e:
                print(f"Error in handle_submit: {e}")

    def on_tree_expand(self, item):
        self.progress_bar.setValue(0)
        if item.childCount() == 1 and item.child(0).text(0) == "Loading...":
            item.takeChildren()
            node_info = item.data(0, Qt.UserRole)
            if not node_info or "type" not in node_info:
                return

            if node_info["type"] == "job":
                folders = query_folder_content_info(node_info["id"])

                self.folder_thread = QThread()
                self.folder_worker = FolderExpansionWorker(
                    job_id=node_info["id"],
                    folders=folders,
                    compare_fn=self.compare_db_and_drive_folders
                )
                self.folder_worker.moveToThread(self.folder_thread)

                self.folder_worker.progress.connect(self.update_progress_bar)
                self.folder_worker.finished.connect(lambda folder_map: self.on_folders_loaded(item, folder_map))
                self.folder_worker.error.connect(lambda msg: print(f"[Worker error] {msg}"))

                self.folder_thread.started.connect(self.folder_worker.run)
                self.folder_worker.finished.connect(self.folder_thread.quit)
                self.folder_worker.finished.connect(self.folder_worker.deleteLater)
                self.folder_thread.finished.connect(self.folder_thread.deleteLater)

                self.folder_thread.start()

            elif node_info["type"] == "folder":
                permissions = query_permissions_info(node_info["id"])
                for principal, perm, inh_type, inh_source in permissions:
                    item.addChild(QTreeWidgetItem(["", "", principal, perm, inh_type, inh_source]))
                self.progress_bar.setValue(100)
                node_info["loaded"] = True
                item.setData(0, Qt.UserRole, node_info)

    def on_tree_item_clicked(self, item, column):
        try:
            self.progress_bar.setValue(13)

            node_info = item.data(0, Qt.UserRole)
            if not node_info or "type" not in node_info:
                return

            if node_info["type"] == "folder":
                self.start_progress_animation()
                folder_id = node_info["id"]

                # Threading begins here
                self.permission_thread = QThread()
                self.permission_worker = PermissionLoaderWorker(folder_id)
                self.permission_worker.moveToThread(self.permission_thread)

                self.permission_worker.finished.connect(lambda perms: self.on_permissions_loaded(perms, folder_id))
                self.permission_worker.error.connect(lambda msg: print(f"[Permission worker error] {msg}"))

                self.permission_thread.started.connect(self.permission_worker.run)
                self.permission_worker.finished.connect(self.permission_thread.quit)
                self.permission_worker.finished.connect(self.permission_worker.deleteLater)
                self.permission_thread.finished.connect(self.permission_thread.deleteLater)

                self.permission_thread.start()

        except Exception as e:
            print(f"Error handling item click: {e}")

    def reset_tree(self,item):
        try:
            node_info = item.data(0, Qt.UserRole)
            if not node_info or "type" not in node_info:
                return

            # Reset only if the item is a folder
            if node_info["type"] == "folder":
                # Clear the permission columns
                item.setText(2, "")
                item.setText(3, "")
                item.setText(4, "")
                item.setText(5, "")

                # Mark the node as not loaded (if needed for reloading)
                node_info["loaded"] = False
                item.setData(0, Qt.UserRole, node_info)
                self.progress_bar.setValue(0)

        except Exception as e:
            print(f"Error resetting tree item: {e}")

    def add_subfolders(self, parent_item, parent_id, folder_map):

        for folder_id, folder_owner, folder_path in folder_map.get(parent_id, []):

            relative_path = os.path.basename(folder_path)

            # Create a tree item for this folder
            folder_item = QTreeWidgetItem([relative_path, folder_owner, "", "", "", ""])
            folder_item.setData(0, Qt.UserRole,
                                {"type": "folder", "id": folder_id, "path": folder_path, "parent_folder": parent_id,
                                 "loaded": False})

            #print("I am now")
            # Add this folder to the parent item
            parent_item.addChild(folder_item)

            #
            self.add_subfolders(folder_item, folder_id, folder_map)

    def populate_jobs(self, job_info):
        try:
            for job_id,job_info in job_info:

                job_branch = QTreeWidgetItem([job_info, "", "", "", "", ""])
                job_branch.setData(0, Qt.UserRole, {"type": "job", "id": job_id})
                job_branch.addChild(QTreeWidgetItem(["Loading..."]))
                self.tree_widget.addTopLevelItem(job_branch)

        except Exception as e:
            print(f"Error in populate_jobs: {e}")

    def update_progress_bar(self, value):

        self.progress_bar.setValue(value)

    def compare_db_and_drive_folders(self,folder_path,db_date_modified,job_id,parent_folder):
        try:
            folder_exist = os.path.exists(folder_path)
            if folder_exist:
                #self.progress_bar.setValue(10)
                if db_date_modified is not None: #makes sure the folder is in DB and drive

                    #THE DB is up to date with the drive
                    db_datetime = datetime.strptime(db_date_modified, '%Y-%m-%d %H:%M:%S')
                    filesystem_date_modified = datetime.fromtimestamp(os.path.getmtime(folder_path)).replace(microsecond=0)
                    if db_datetime >= filesystem_date_modified:
                        #print("DB is up to date")
                        return "DB up to date"
                    else:

                        # THE DB isn't up to date with the drive
                        print(f"{folder_path} needs to be updated in the DB. Updating...")
                        updated_folder = get_all_principal_permission(folder_path)
                        #print(f"{updated_folder}")
                        update_permissions(folder_path,updated_folder,filesystem_date_modified)
                        return "DB UPDATED"
                else:
                    # The DB doesn't have a folder in the drive
                    print(f"{folder_path} is newer in the filesystem. Adding to DB...")
                    new_folder_owner = get_folder_owner(folder_path)
                    new_folder_date_modified = datetime.fromtimestamp(os.path.getmtime(folder_path)).strftime('%Y-%m-%d %H:%M:%S')
                    new_folder_perms = get_all_principal_permission(folder_path)

                    folder_id = add_folder_content(connection='C:\\Program Files\\DB Browser for SQLite\\TLC_folderpermission.db',job_id=job_id,folder_path=folder_path,folder_owner=new_folder_owner,folder_date_modified=new_folder_date_modified,parent_folder_id=parent_folder)
                    if folder_id:
                        add_permissions(connection='C:\\Program Files\\DB Browser for SQLite\\TLC_folderpermission.db', folder_content_id=folder_id, permissions=new_folder_perms)
                        print(f"Added new folder and permissions for {folder_path}")
                        return "New Folder Added"
                    else:
                        print(f"Failed to add {folder_path} to the database.")
                        return "Error Adding New Folder"

            else:
                # The DB has a folder that has been deleted in the drive
                print(f"{folder_path} doesn't exist... deleting")
                delete_folder(folder_path)
                print(f"delete successful of {folder_path}")
                return "DELETED"
        except Exception as e:
            print(f"Error in compare_db_and_drive_folders: {e}")

    def update_permissions_table(self, folder_id, permissions):
        self.permissions_table.setRowCount(0)
        self.permissions_table.setUpdatesEnabled(False)


        explicit_keys = {
            f"{principal}+{perm}"
            for principal, perm, scope, source in permissions
            if source == "Set Here"
        }

        seen_permissions = set()
        rows_to_add = []


        for principal, perm, scope, source in permissions:
            base_key = f"{principal}+{perm}"
            full_key = f"{principal}+{perm}+{scope}+{source}"


            if source != "Set Here" and base_key in explicit_keys:
                #print(f"Skipping inherited {principal} ({perm}) — already has Set Here")
                continue

            # Avoid duplicate exact entries
            if full_key in seen_permissions:
                continue

            rows_to_add.append((principal, perm, scope, source))
            seen_permissions.add(full_key)


        self.permissions_table.setRowCount(len(rows_to_add))

        for row_idx, (principal, perm, scope, source) in enumerate(rows_to_add):
            self.permissions_table.setItem(row_idx, 0, QTableWidgetItem(principal))
            self.permissions_table.setItem(row_idx, 1, QTableWidgetItem(perm))
            self.permissions_table.setItem(row_idx, 2, QTableWidgetItem(scope))
            self.permissions_table.setItem(row_idx, 3, QTableWidgetItem(source))

        self.permissions_table.setUpdatesEnabled(True)

    def on_folders_loaded(self, item, folder_map):
        self.add_subfolders(item, None, folder_map)
        node_info = item.data(0, Qt.UserRole)
        if node_info:
            node_info["loaded"] = True
            item.setData(0, Qt.UserRole, node_info)
        self.progress_bar.setValue(100)

    def on_permissions_loaded(self, permissions, folder_id):
        self.stop_progress_animation()
        self.reference_permissions = {
            f"{p}+{perm}": source
            for p, perm, scope, source in permissions
            if source == "Set Here"
        }
        self.update_permissions_table(folder_id, permissions)
        self.progress_bar.setValue(100)

    def start_progress_animation(self):
        self.progress_value = 0
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.animate_progress)
        self.progress_timer.start(40)

    def animate_progress(self):
        if self.progress_value < 95:
            self.progress_value += 1
            self.progress_bar.setValue(self.progress_value)
        else:
            self.progress_timer.stop()

    def stop_progress_animation(self):
        if hasattr(self, 'progress_timer'):
            self.progress_timer.stop()
        self.progress_bar.setValue(100)
