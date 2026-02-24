import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import pandas as pd

DB_FILE = "inventory.db"

# --- Создание базы ---
def create_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            model TEXT NOT NULL,
            serial TEXT NOT NULL,
            user TEXT,
            location TEXT,
            status TEXT,
            notes TEXT
        )
    """)
    conn.commit()
    conn.close()

create_db()

# --- Функция обновления всей таблицы и графиков ---
def refresh_all():
    filters = {
        "type": type_filter.get().strip(),
        "user": user_filter.get().strip(),
        "location": location_filter.get().strip()
    }
    load_equipment(filters)
    update_dashboard(filters if apply_filter_to_graphs.get() else None)

# --- Добавление записи ---
def add_equipment():
    type_ = type_entry.get().strip()
    model = model_entry.get().strip()
    serial = serial_entry.get().strip()
    user = user_entry.get().strip()
    location = location_entry.get().strip()
    status = status_entry.get().strip()
    notes = notes_entry.get().strip()
    if not type_ or not model or not serial:
        messagebox.showwarning("Ошибка", "Заполните обязательные поля")
        return
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO equipment (type, model, serial, user, location, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (type_, model, serial, user, location, status, notes))
    conn.commit()
    conn.close()
    clear_entries()
    refresh_all()

# --- Загрузка данных в таблицу ---
def load_equipment(filters=None):
    for row in tree.get_children():
        tree.delete(row)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    query = "SELECT * FROM equipment"
    params = []
    if filters:
        conditions = []
        for col, val in filters.items():
            if val:
                conditions.append(f"{col} LIKE ?")
                params.append(f"%{val}%")
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    for i, row in enumerate(rows):
        tag = 'odd' if i % 2 else 'even'
        if row[6].lower() == 'неисправен':
            tag = 'error'
        display_notes = row[7]  # показываем всё примечание целиком
        tree.insert("", "end", values=(row[0], row[1], row[2], row[3], row[4], row[5], row[6], display_notes), tags=(tag,))
    auto_resize_columns()
    conn.close()

# --- Очистка полей ---
def clear_entries():
    for entry in entries:
        entry.delete(0, tk.END)

# --- Удаление записи ---
def delete_equipment():
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("Ошибка", "Выберите запись для удаления")
        return
    record_id = tree.item(selected)["values"][0]
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM equipment WHERE id=?", (record_id,))
    conn.commit()
    conn.close()
    refresh_all()

# --- Редактирование записи ---
def edit_equipment():
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("Ошибка", "Выберите запись для редактирования")
        return
    record = tree.item(selected)["values"]
    type_entry.delete(0, tk.END)
    type_entry.insert(0, record[1])
    model_entry.delete(0, tk.END)
    model_entry.insert(0, record[2])
    serial_entry.delete(0, tk.END)
    serial_entry.insert(0, record[3])
    user_entry.delete(0, tk.END)
    user_entry.insert(0, record[4])
    location_entry.delete(0, tk.END)
    location_entry.insert(0, record[5])
    status_entry.delete(0, tk.END)
    status_entry.insert(0, record[6])
    notes_entry.delete(0, tk.END)
    notes_entry.insert(0, record[7])
    save_btn.config(command=lambda: save_edit(record[0]))

# --- Сохранение изменений после редактирования ---
def save_edit(record_id):
    type_ = type_entry.get().strip()
    model = model_entry.get().strip()
    serial = serial_entry.get().strip()
    user = user_entry.get().strip()
    location = location_entry.get().strip()
    status = status_entry.get().strip()
    notes = notes_entry.get().strip()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE equipment
        SET type=?, model=?, serial=?, user=?, location=?, status=?, notes=?
        WHERE id=?
    """, (type_, model, serial, user, location, status, notes, record_id))
    conn.commit()
    conn.close()
    clear_entries()
    refresh_all()

# --- Экспорт CSV ---
def export_csv():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM equipment", conn)
    df.to_csv("equipment_export.csv", index=False)
    conn.close()
    messagebox.showinfo("Экспорт", "Данные экспортированы в equipment_export.csv")

# --- Применение фильтров ---
def apply_filter(*args):
    refresh_all()

# --- Дашборд ---
def update_dashboard(filters=None):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM equipment", conn)
    conn.close()
    if filters is not None:
        for col, val in filters.items():
            if val:
                df = df[df[col].str.contains(val, case=False, na=False)]
    ax1.clear()
    ax2.clear()
    if not df.empty:
        counts_type = df['type'].value_counts()
        counts_type.plot(kind='bar', ax=ax1, color='skyblue')
        ax1.set_title("Количество устройств по типу")
        ax1.set_ylabel("Количество")
        ax1.set_xlabel("Тип")
        counts_status = df[df['status'].str.lower() == 'неисправен']['type'].value_counts()
        if not counts_status.empty:  # проверка пустой серии
            counts_status.plot(kind='bar', ax=ax2, color='red')
        ax2.set_title("Неисправные устройства по типу")
        ax2.set_ylabel("Количество")
        ax2.set_xlabel("Тип")
    canvas.draw()

# --- Авто-ширина колонок ---
def auto_resize_columns():
    for col in columns:
        if col == "Примечания":
            tree.column(col, width=350)
            continue
        max_width = max([len(str(tree.set(k, col))) for k in tree.get_children()] + [len(col)]) * 10
        tree.column(col, width=max(max_width, 80))

# --- Сортировка по колонкам ---
sort_orders = {}
def sort_column(col):
    data = [(tree.set(k, col), k) for k in tree.get_children()]
    order = sort_orders.get(col, True)
    data.sort(reverse=not order)
    for index, (val, k) in enumerate(data):
        tree.move(k, '', index)
    sort_orders[col] = not order
    refresh_all()

# --- Просмотр/редактирование примечаний ---
def view_notes(event):
    selected = tree.selection()
    if not selected:
        return
    record = tree.item(selected)["values"]
    notes_text = record[7] if record[7] else ""
    top = tk.Toplevel(root)
    top.title("Примечания")
    top.geometry("500x300")
    txt = tk.Text(top, wrap="word")
    txt.insert("1.0", notes_text)
    txt.pack(expand=True, fill="both")
    def save_notes():
        new_notes = txt.get("1.0", "end").strip()
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE equipment SET notes=? WHERE id=?", (new_notes, record[0]))
        conn.commit()
        conn.close()
        top.destroy()
        refresh_all()
    tk.Button(top, text="Сохранить", command=save_notes, bg="#2196F3", fg="white").pack(pady=5)

# --- Главное окно ---
root = tk.Tk()
root.title("Инвентаризация IT — финальный вариант")
root.geometry("1250x800")
root.resizable(False, False)

# --- Галочка фильтров для графиков ---
apply_filter_to_graphs = tk.BooleanVar()
tk.Checkbutton(root, text="Применять фильтры к графикам", variable=apply_filter_to_graphs,
               onvalue=True, offvalue=False, command=refresh_all).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=5)

# --- Дашборд ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10,3))
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().grid(row=1, column=0, columnspan=6, padx=10, pady=5)

# --- Поля ввода ---
labels = ["Тип", "Модель", "Серийный номер", "Пользователь", "Локация", "Состояние", "Примечания"]
entries = []
for i, text in enumerate(labels):
    tk.Label(root, text=text).grid(row=i+2, column=0, sticky="w", padx=5, pady=2)
    entry = tk.Entry(root, width=50)
    entry.grid(row=i+2, column=1, columnspan=5, padx=5, pady=2)
    entries.append(entry)
type_entry, model_entry, serial_entry, user_entry, location_entry, status_entry, notes_entry = entries

# --- Кнопки ---
tk.Button(root, text="Добавить", command=add_equipment, width=18, bg="#4CAF50", fg="white").grid(row=9, column=0, pady=5)
save_btn = tk.Button(root, text="Сохранить изменения", width=18, bg="#2196F3", fg="white")
save_btn.grid(row=9, column=1, pady=5)
tk.Button(root, text="Редактировать выбранное", command=edit_equipment, width=18, bg="#FF9800", fg="white").grid(row=9, column=2, pady=5)
tk.Button(root, text="Удалить выбранное", command=delete_equipment, width=18, bg="#f44336", fg="white").grid(row=9, column=3, pady=5)
tk.Button(root, text="Экспорт CSV", command=export_csv, width=54, bg="#9C27B0", fg="white").grid(row=10, column=0, columnspan=6, pady=5)

# --- Фильтры ---
tk.Label(root, text="Фильтр по типу:").grid(row=11, column=0, sticky="w", padx=5)
type_filter = tk.Entry(root, width=20)
type_filter.grid(row=11, column=1, padx=5)
type_filter.bind("<KeyRelease>", apply_filter)
tk.Label(root, text="Фильтр по пользователю:").grid(row=11, column=2, sticky="w", padx=5)
user_filter = tk.Entry(root, width=20)
user_filter.grid(row=11, column=3, padx=5)
user_filter.bind("<KeyRelease>", apply_filter)
tk.Label(root, text="Фильтр по локации:").grid(row=11, column=4, sticky="w", padx=5)
location_filter = tk.Entry(root, width=20)
location_filter.grid(row=11, column=5, padx=5)
location_filter.bind("<KeyRelease>", apply_filter)

# --- Таблица ---
columns = ("ID", "Тип", "Модель", "Серийный номер", "Пользователь", "Локация", "Состояние", "Примечания")
tree = ttk.Treeview(root, columns=columns, show="headings", height=15)
for col in columns:
    width = 350 if col == "Примечания" else 120
    tree.heading(col, text=col, command=lambda c=col: sort_column(c))
    tree.column(col, width=width)
tree.grid(row=12, column=0, columnspan=6, pady=10)
scrollbar = ttk.Scrollbar(root, orient="vertical", command=tree.yview)
tree.configure(yscroll=scrollbar.set)
scrollbar.grid(row=12, column=6, sticky="ns", pady=10)

tree.tag_configure('even', background='#f2f2f2')
tree.tag_configure('odd', background='white')
tree.tag_configure('error', background='#ffcccc')

tree.bind("<Double-1>", view_notes)

refresh_all()
root.mainloop()