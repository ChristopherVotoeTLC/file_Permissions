import os
import pyodbc as db
from dotenv import load_dotenv


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


# dbo.UU_PCA_Projects
def get_project_info(root_path, db_connection):
    try:
        folder_name = os.path.basename(root_path)
        project_number = folder_name.split('-')[0]

        cursor = db_connection.cursor()
        cursor.execute("""
                       SELECT TOP(1) p.[Project_Number], p.[Project_Name],
                              e.[emp_name],
                              d.[D_sname],
                              d.[D_adm_name]
                       FROM [dbo].[UU_PCA_Projects] p
                           LEFT JOIN [dbo].[UU_Emps_All] e
                       ON p.[Project_PM_Number] = e.[emp_code]
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
