import os
import mysql.connector
from mysql.connector import Error
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
from dotenv import load_dotenv

load_dotenv()

class DatabaseManager:
    def __init__(self, host, port, user, password, database): #nawiązanie połączenia z bazą
        self.connection = None
        try:
            self.connection = mysql.connector.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database
            )
            if self.connection.is_connected():
                print("Połączono z bazą danych.")
        except Error as e:
            messagebox.showerror("Błąd połączenia", f"Nie udało się połączyć z bazą danych: {e}")

    def get_tables(self): #pobiera listę tabel w bazie danych
        try:
            cursor = self.connection.cursor()
            cursor.execute("SHOW TABLES;")
            tables = [table[0] for table in cursor.fetchall()]
            return tables
        except Error as e:
            messagebox.showerror("Błąd", f"Nie udało się pobrać tabel: {e}")
            return []

    def get_data(self, table_name): #pobiera wszystkie dane z wybranej tabeli
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"SELECT * FROM {table_name};")
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            return columns, rows
        except Error as e:
            messagebox.showerror("Błąd", f"Nie udało się pobrać danych z tabeli {table_name}: {e}")
            return [], []

    def update_data(self, table_name, columns, values, primary_key_column, primary_key_value): #aktualizuje istniejący rekord w tabeli
        try:
            cursor = self.connection.cursor()

            #zamiana wartości None na NULL
            processed_values = [value if value is not None and value != "" else None for value in values]

            set_clause = ", ".join([f"{col} = %s" for col in columns])
            query = f"UPDATE {table_name} SET {set_clause} WHERE {primary_key_column} = %s;"

            #wykonaj zapytanie
            cursor.execute(query, processed_values + [primary_key_value])
            self.connection.commit()

            messagebox.showinfo("Sukces", "Rekord został zaktualizowany.")
        except Error as e:
            messagebox.showerror("Błąd", f"Nie udało się zaktualizować rekordu: {e}")

    def delete_data(self, table_name, column_name, value): #usuwa rekord z tabeli
        try:
            cursor = self.connection.cursor()
            query = f"DELETE FROM {table_name} WHERE {column_name} = %s;"
            cursor.execute(query, (value,))
            self.connection.commit()
            messagebox.showinfo("Sukces", "Rekord został usunięty.")
        except Error as e:
            messagebox.showerror("Błąd", f"Nie udało się usunąć rekordu: {e}")

    def get_foreign_key_options(self, table_name,
                                column_name):  # pobiera możliwe opcje dla kolumn będących kluczami obcymi
        cursor = self.connection.cursor()
        query = """
        SELECT 
            kcu.REFERENCED_TABLE_NAME, 
            kcu.REFERENCED_COLUMN_NAME
        FROM information_schema.KEY_COLUMN_USAGE kcu
        WHERE kcu.TABLE_NAME = %s AND kcu.COLUMN_NAME = %s
        AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
        AND kcu.TABLE_SCHEMA = DATABASE();
        """
        cursor.execute(query, (table_name, column_name))
        result = cursor.fetchone()

        if result:
            referenced_table, referenced_column = result
            cursor.execute(f"SELECT {referenced_column} FROM {referenced_table}")
            options = [row[0] for row in cursor.fetchall()]
        else:
            options = []

        cursor.close()
        return options

    def get_foreign_keys(self, table_name):
        try:
            cursor = self.connection.cursor()
            query = """
            SELECT COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_NAME = %s AND TABLE_SCHEMA = DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL;
            """
            cursor.execute(query, (table_name,))
            foreign_keys = cursor.fetchall()
            return foreign_keys
        except Error as e:
            messagebox.showerror("Błąd", f"Nie udało się pobrać kluczy obcych z tabeli {table_name}: {e}")
            return []

    def insert_data(self, table_name, columns, values): #dodaje nowy rekord do tabeli
        try:
            cursor = self.connection.cursor()
            placeholders = ", ".join(["%s"] * len(values))
            columns_str = ", ".join(columns)
            query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
            cursor.execute(query, values)
            self.connection.commit()
            messagebox.showinfo("Sukces", "Rekord został dodany pomyślnie.")
        except Error as e:
            messagebox.showerror("Błąd", f"Nie udało się dodać rekordu: {e}")

#interfejs graficzny aplikacji umożliwiający przeglądanie i modyfikowanie danych
class DataManagementApp:
    def __init__(self, root, db_manager):

        self.root = root
        self.db_manager = db_manager
        self.current_table = None

        self.root.title("Zarządzanie danymi w bazie")
        style = ttk.Style()
        style.theme_use("clam")

        # UI: Wybór tabeli
        self.table_selector = ttk.Combobox(root, state="readonly")
        self.table_selector['values'] = self.db_manager.get_tables()
        self.table_selector.bind("<<ComboboxSelected>>", self.load_table_data)
        self.table_selector.pack(pady=10)

        # UI: Tabela danych
        self.tree = ttk.Treeview(root, show="headings")
        self.tree.pack(fill=tk.BOTH, expand=True, pady=10)

        # UI: Przyciski
        button_frame = tk.Frame(root)
        button_frame.pack(pady=10)

        self.add_button = tk.Button(button_frame, text="Dodaj rekord", command=self.add_record)
        self.add_button.grid(row=0, column=0, padx=5)

        self.edit_button = tk.Button(button_frame, text="Edytuj rekord", command=self.edit_record)
        self.edit_button.grid(row=0, column=1, padx=5)

        self.delete_button = tk.Button(button_frame, text="Usuń rekord", command=self.delete_record)
        self.delete_button.grid(row=0, column=2, padx=5)

        self.view_related_button = tk.Button(button_frame, text="Pokaż powiązane dane", command=self.show_related_data)
        self.view_related_button.grid(row=0, column=3, padx=5)

        self.report_button = tk.Button(button_frame, text="Wygeneruj raport", command=self.open_report_window)
        self.report_button.grid(row=0, column=4, padx=5)

    def open_report_window(self):
        def open_param_window(report_type):
            """Otwarcie okna do wprowadzania parametrów dla raportu."""
            param_window = tk.Toplevel(self.root)
            param_window.title("Podaj parametry")
            param_window.geometry("300x200")

            if report_type == "Wykres":
                tk.Label(param_window, text="Data początkowa (YYYY-MM-DD):").pack(pady=5)
                start_date_entry = tk.Entry(param_window, width=20)
                start_date_entry.pack(pady=5)

                tk.Label(param_window, text="Data końcowa (YYYY-MM-DD):").pack(pady=5)
                end_date_entry = tk.Entry(param_window, width=20)
                end_date_entry.pack(pady=5)

                def submit_params():
                    start_date = start_date_entry.get().strip()
                    end_date = end_date_entry.get().strip()
                    if not start_date or not end_date:
                        messagebox.showerror("Błąd", "Wprowadź obie daty.")
                        return
                    param_window.destroy()
                    subprocess.run(["python", "raport.py", "2", start_date, end_date])  # Wywołanie raportu z wykresem
                    messagebox.showinfo("Sukces", "Raport został zapisany jako \"liczba_dostaw.pdf\".")

                tk.Button(param_window, text="Wygeneruj raport", command=submit_params).pack(pady=10)

            elif report_type == "Formularz":
                tk.Label(param_window, text="ID przesyłki:").pack(pady=5)
                przesylka_id_entry = tk.Entry(param_window, width=20)
                przesylka_id_entry.pack(pady=5)

                def submit_params():
                    przesylka_id = przesylka_id_entry.get().strip()
                    if not przesylka_id:
                        messagebox.showerror("Błąd", "Podaj ID przesyłki.")
                        return
                    param_window.destroy()
                    subprocess.run(["python", "raport.py", "3", przesylka_id])  # Wywołanie raportu w formie formularza
                    messagebox.showinfo("Sukces", "Raport został zapisany jako \"szczegoly_przesylki.pdf\".")

                tk.Button(param_window, text="Wygeneruj raport", command=submit_params).pack(pady=10)

        def generate_grouped_report():
            subprocess.run(["python", "raport.py", "1"])  # Wywołanie raportu z grupowaniem
            messagebox.showinfo("Sukces", "Raport został zapisany jako \"lista_pracownikow.pdf\".")

        #główne okno wyboru raportu
        report_window = tk.Toplevel(self.root)
        report_window.title("Wybierz typ raportu")
        report_window.geometry("400x200")

        tk.Label(report_window, text="Wybierz rodzaj raportu:").pack(pady=10)

        tk.Button(report_window, text="Lista pracowników na danych stanowiskach",
                  command=lambda: [report_window.destroy(), generate_grouped_report()]).pack(pady=5)
        tk.Button(report_window, text="Realizacja dostaw przez kurierów w określonym czasie",
                  command=lambda: [report_window.destroy(), open_param_window("Wykres")]).pack(pady=5)
        tk.Button(report_window, text="Szczegóły przesyłki",
                  command=lambda: [report_window.destroy(), open_param_window("Formularz")]).pack(pady=5)

    def load_table_data(self, event=None): #Ładuje dane z wybranej tabeli.
        self.current_table = self.table_selector.get()
        columns, rows = self.db_manager.get_data(self.current_table)

        # Czyszczenie tabeli
        self.tree.delete(*self.tree.get_children())
        self.tree['columns'] = columns

        # Ustawianie nagłówków
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor=tk.W)

        # Dodanie danych do tabeli
        for row in rows:
            self.tree.insert("", "end", values=row)

    def show_related_data(self):
        if not self.current_table:
            messagebox.showerror("Błąd", "Najpierw wybierz tabelę.")
            return

        # Pobieranie kluczy obcych tabeli
        foreign_keys = self.db_manager.get_foreign_keys(self.current_table)

        if not foreign_keys:
            messagebox.showinfo("Informacja", "Brak powiązań kluczy obcych w tej tabeli.")
            return

        # Sprawdzanie, czy jedna z powiązanych tabel to 'przesyłka'
        related_tables = [ref_table for _, ref_table, _ in foreign_keys]
        if 'przesyłka' in related_tables:
            # Dodanie nadawcy i adresata, jeśli przesyłka jest powiązana
            related_tables.extend(['nadawca', 'adresat'])

        # Tworzenie nowego okna dialogowego
        related_window = tk.Toplevel(self.root)
        related_window.title("Powiązane dane")
        related_window.geometry("600x400")  # Ustawienie początkowych, mniejszych wymiarów
        related_window.minsize(600, 400)

        # Dodanie canvas i scrollbar
        canvas = tk.Canvas(related_window)
        scrollbar = ttk.Scrollbar(related_window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Wyświetlanie danych powiązanych tabel
        for i, (fk_column, ref_table, ref_column) in enumerate(foreign_keys):
            tk.Label(scrollable_frame, text=f"Powiązane dane dla: {fk_column} → {ref_table} ({ref_column})",
                     font=("Arial", 12, "bold")).pack(pady=5)

            # Pobranie danych z tabeli powiązanej
            columns, rows = self.db_manager.get_data(ref_table)

            if not rows:
                tk.Label(scrollable_frame, text="Brak danych w powiązanej tabeli").pack(pady=5)
                continue

            # Tworzenie TreeView dla danych
            related_tree = ttk.Treeview(scrollable_frame, show="headings", height=8)
            related_tree["columns"] = columns

            for col in columns:
                related_tree.heading(col, text=col)
                related_tree.column(col, width=100, anchor="w")

            for row in rows:
                related_tree.insert("", "end", values=row)

            related_tree.pack(fill="x", padx=10, pady=5)

        # Sprawdzanie, czy 'przesyłka' była wśród powiązanych tabel
        if 'przesylka' in related_tables:
            # Dodatkowo pokazujemy dane nadawcy i adresata
            for ref_table in ['nadawca', 'adresat']:
                columns, rows = self.db_manager.get_data(ref_table)

                if rows:
                    tk.Label(scrollable_frame, text=f"Powiązane dane dla: {ref_table}",
                             font=("Arial", 12, "bold")).pack(pady=5)

                    related_tree = ttk.Treeview(scrollable_frame, show="headings", height=8)
                    related_tree["columns"] = columns

                    for col in columns:
                        related_tree.heading(col, text=col)
                        related_tree.column(col, width=100, anchor="w")

                    for row in rows:
                        related_tree.insert("", "end", values=row)

                    related_tree.pack(fill="x", padx=10, pady=5)

        # Automatyczne dostosowanie rozmiaru do ekranu (mniejsze okno)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        max_width = min(screen_width, 800)
        max_height = min(screen_height, 600)
        related_window.geometry(f"{max_width}x{max_height}")

    def add_record(self): #dodanie nowego rekordu do aktualnie wybranej tabeli.
        if not self.current_table:
            messagebox.showerror("Błąd", "Najpierw wybierz tabelę.")
            return

        #pobierz informacje o kolumnach
        cursor = self.db_manager.connection.cursor()
        cursor.execute(f"SHOW COLUMNS FROM {self.current_table};")
        columns_info = cursor.fetchall()

        #filtrujemy kolumny, które nie są AUTO_INCREMENT
        editable_columns = [
            col[0] for col in columns_info if
            "auto_increment" not in col[5].lower()
        ]
        if self.current_table == "przesylka": #specjalne traktowanie tabeli przesylka
            form_window = tk.Toplevel(self.root)
            form_window.title(f"Dodaj rekord do tabeli: {self.current_table}")

            entries = {}

            #dodajemy pola dla ID_nadawcy, ID_adresata, waga, rozmiar, forma_platnosci
            labels_and_entries = [
                ("ID Nadawcy", "ID_nadawcy"),
                ("ID Adresata", "ID_adresata"),
                ("Waga", "waga"),
                ("Rozmiar", "rozmiar"),
                ("Forma płatności", "forma_platnosci")
            ]

            for i, (label, column) in enumerate(labels_and_entries):
                tk.Label(form_window, text=label).grid(row=i, column=0, padx=10, pady=5, sticky=tk.W)
                entry = tk.Entry(form_window, width=30)
                entry.grid(row=i, column=1, padx=10, pady=5)
                entries[column] = entry

            # Funkcja do dodania przesyłki
            def save_record_with_procedure():
                try:
                    values = [
                        entries["ID_nadawcy"].get(),
                        entries["ID_adresata"].get(),
                        entries["waga"].get(),
                        entries["rozmiar"].get(),
                        entries["forma_platnosci"].get()
                    ]

                    # Wywołanie procedury Dodaj_Nowa_Przesylke
                    cursor.callproc("Dodaj_Nowa_Przesylke", values)
                    self.db_manager.connection.commit()

                    messagebox.showinfo("Sukces", "Rekord został dodany przez procedurę.")
                    form_window.destroy()
                    self.load_table_data()
                except Error as e:
                    messagebox.showerror("Błąd", f"Nie udało się dodać rekordu przez procedurę: {e}")

            save_button = tk.Button(form_window, text="Zapisz", command=save_record_with_procedure)
            save_button.grid(row=len(labels_and_entries), column=0, columnspan=2, pady=10)

            form_window.mainloop()

        else:
            form_window = tk.Toplevel(self.root)
            form_window.title(f"Dodaj rekord do tabeli: {self.current_table}")

            entries = {}

            for i, column in enumerate(editable_columns):
                tk.Label(form_window, text=column).grid(row=i, column=0, padx=10, pady=5, sticky=tk.W)

                # Obsługa kluczy obcych
                options = self.db_manager.get_foreign_key_options(self.current_table, column)
                if options:
                    combobox = ttk.Combobox(form_window, values=options, state="readonly")
                    combobox.grid(row=i, column=1, padx=10, pady=5)
                    entries[column] = combobox
                else:
                    # Obsługa zwykłych pól tekstowych
                    entry = tk.Entry(form_window, width=30)
                    entry.grid(row=i, column=1, padx=10, pady=5)
                    entries[column] = entry

            def save_record():
                new_values = [entry.get() for entry in entries.values()]

                # Sprawdź, czy wszystkie pola są wypełnione
                if any(not value for value in new_values):
                    messagebox.showerror("Błąd", "Wszystkie pola muszą być wypełnione.")
                    return

                # Wstaw nowy rekord do bazy danych
                self.db_manager.insert_data(self.current_table, editable_columns, new_values)
                form_window.destroy()
                self.load_table_data()

            save_button = tk.Button(form_window, text="Zapisz rekord", command=save_record)
            save_button.grid(row=len(editable_columns), column=0, columnspan=2, pady=10)

            form_window.mainloop()

    def edit_record(self): #edycja rekordu
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showerror("Błąd", "Wybierz rekord do edycji.")
            return

        selected_values = self.tree.item(selected_item[0])['values']

        form_window = tk.Toplevel(self.root)
        form_window.title(f"Edytuj rekord w tabeli: {self.current_table}")

        entries = {}

        for i, column in enumerate(self.tree["columns"]):
            label = tk.Label(form_window, text=column)
            label.grid(row=i, column=0)
            entry = tk.Entry(form_window)
            entry.grid(row=i, column=1)
            entry.insert(0,
                         selected_values[i] if selected_values[i] is not None else "")  # Wyświetl pusty string dla None
            entries[column] = entry

        # Funkcja do zapisywania zmian
        def save_changes():
            updated_values = [
                entries[column].get() if entries[column].get() != "" else None
                for column in self.tree["columns"]
            ]
            primary_key_value = selected_values[0]  # Zakładamy, że pierwsza kolumna to klucz główny

            if primary_key_value is None:
                messagebox.showerror("Błąd", "Nie można edytować rekordu bez klucza głównego.")
                return

            columns_to_update = self.tree["columns"]
            self.db_manager.update_data(self.current_table, columns_to_update, updated_values, columns_to_update[0],
                                        primary_key_value)
            form_window.destroy()
            self.load_table_data()  # Odśwież tabelę

        save_button = tk.Button(form_window, text="Zapisz zmiany", command=save_changes)
        save_button.grid(row=len(self.tree["columns"]), column=0, columnspan=2)


    def delete_record(self): #usuwanie wybranego rekordu
        if not self.current_table:
            messagebox.showerror("Błąd", "Najpierw wybierz tabelę.")
            return

        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showerror("Błąd", "Wybierz rekord do usunięcia.")
            return

        # Pobierz nazwę klucza głównego dla aktualnej tabeli
        cursor = self.db_manager.connection.cursor()
        cursor.execute(f"SHOW KEYS FROM {self.current_table} WHERE Key_name = 'PRIMARY';")
        primary_key_info = cursor.fetchone()

        selected_values = self.tree.item(selected_item[0])['values']
        if primary_key_info:
            # Usuwanie przy użyciu klucza głównego
            primary_key_column = primary_key_info[4]  # Kolumna klucza głównego
            primary_key_value = selected_values[
                0]  # Zakładamy, że klucz główny jest w pierwszej kolumnie (zgodnej z TreeView)

            confirmation = messagebox.askyesno(
                "Potwierdzenie",
                f"Czy na pewno chcesz usunąć rekord o wartości {primary_key_value}?"
            )
            if confirmation:
                self.db_manager.delete_data(self.current_table, primary_key_column, primary_key_value)
                self.load_table_data()  # Odśwież tabelę
        else:
            # Obsługa tabeli bez klucza głównego
            confirmation = messagebox.askyesno(
                "Potwierdzenie",
                f"Nie znaleziono klucza głównego.\nCzy na pewno chcesz usunąć ten rekord?"
            )
            if confirmation:
                self.delete_data_without_primary_key(self.current_table, selected_values)
                self.load_table_data()

    def delete_data_without_primary_key(self, table_name, row_values):
        """
        Usuwa rekord z tabeli bez klucza głównego.
        Tworzy zapytanie `DELETE` na podstawie wszystkich wartości z wiersza.
        """
        try:
            #pobierz kolumny tabeli
            columns, _ = self.db_manager.get_data(table_name)

            #utwórz zapytanie DELETE
            conditions = []
            for column, value in zip(columns, row_values):
                if value is None:  # Obsługa wartości NULL
                    conditions.append(f"`{column}` IS NULL")
                else:
                    conditions.append(f"`{column}` = %s")
            condition_clause = " AND ".join(conditions)
            query = f"DELETE FROM `{table_name}` WHERE {condition_clause} LIMIT 1;"

            # Wykonaj zapytanie
            cursor = self.db_manager.connection.cursor()
            cursor.execute(query, [val for val in row_values if val is not None])
            self.db_manager.connection.commit()

            messagebox.showinfo("Sukces", "Rekord został usunięty.")
        except Error as e:
            messagebox.showerror("Błąd", f"Nie udało się usunąć rekordu: {e}")


host = os.getenv("DB_HOST")
port = int(os.getenv("DB_PORT"))
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
database = os.getenv("DB_NAME")

#tworzenie obiektu zarządzania bazą danych
db_manager = DatabaseManager(host, port, user, password, database)

#tworzenie głównego okna aplikacji
root = tk.Tk()
app = DataManagementApp(root, db_manager)
root.mainloop()
