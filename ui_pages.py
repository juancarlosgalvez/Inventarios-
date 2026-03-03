import customtkinter as ctk
from tkinter import messagebox, filedialog
from services import InventoryService
from reports import ReportGenerator
from auth import db_authenticate, ldap_authenticate