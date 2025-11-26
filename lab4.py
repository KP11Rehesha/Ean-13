import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from PIL import Image, ImageTk, ImageDraw, ImageFont
import psycopg2



DB_CONFIG = {
    "dbname": "Barcode",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": "5432",


    "options": "-c client_encoding=utf8"
}


def db_connect():
    return psycopg2.connect(**DB_CONFIG)


def db_add_product(name, code):
    conn = db_connect()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO products (name, ean_code) VALUES (%s, %s)", (name, code))
        conn.commit()
        return True
    except psycopg2.IntegrityError:
        conn.rollback()
        messagebox.showerror("Дублікат", f"Товар з кодом {code} вже є в базі!")
        return False
    except Exception as e:
        conn.rollback()
        messagebox.showerror("Помилка БД", str(e))
        return False
    finally:
        conn.close()


def db_find_product(code):
    conn = db_connect()
    cur = conn.cursor()
    result_text = ""
    try:
        cur.execute("SELECT id, name, created_at FROM products WHERE ean_code = %s", (code,))
        row = cur.fetchone()
        if row:
            prod_id, name, created_at = row
            date_str = created_at.strftime("%Y-%m-%d %H:%M")
            result_text = f"ЗНАЙДЕНО В БД:\nID: {prod_id}\nНазва: {name}\nДата: {date_str}"
        else:
            result_text = f"Код {code} вірний,\nале в базі такого товару немає."
    except Exception as e:
        result_text = f"Помилка: {str(e)}"
    finally:
        conn.close()
        return result_text


def db_get_all_products():

    conn = db_connect()
    cur = conn.cursor()
    rows = []
    try:

        cur.execute("SELECT id, name, ean_code, created_at FROM products ORDER BY id DESC")
        rows = cur.fetchall()
    except Exception as e:
        messagebox.showerror("Помилка завантаження", str(e))
    finally:
        conn.close()
        return rows



class EAN13ManualGenerator:
    def __init__(self):
        self.L_CODES = ["0001101", "0011001", "0010011", "0111101", "0100011", "0110001", "0101111", "0111011",
                        "0110111", "0001011"]
        self.G_CODES = ["0100111", "0110011", "0011011", "0100001", "0011101", "0111001", "0000101", "0010001",
                        "0001001", "0010111"]
        self.R_CODES = ["1110010", "1100110", "1101100", "1000010", "1011100", "1001110", "1010000", "1000100",
                        "1001000", "1110100"]
        self.PARITY_PATTERNS = ["LLLLLL", "LLGLGG", "LLGGLG", "LLGGGL", "LGLLGG", "LGGLLG", "LGGGLL", "LGLGLG",
                                "LGLGGL", "LGGLGL"]

    def calculate_check_digit(self, code_12):
        sum_odd = sum(int(code_12[i]) for i in range(0, 12, 2))
        sum_even = sum(int(code_12[i]) for i in range(1, 12, 2))
        total = sum_odd + (sum_even * 3)
        rem = total % 10
        return 0 if rem == 0 else 10 - rem

    def generate_image(self, code_input):
        if len(code_input) != 12 or not code_input.isdigit():
            raise ValueError("Треба 12 цифр")
        check = self.calculate_check_digit(code_input)
        full = code_input + str(check)

        first = int(full[0])
        left = full[1:7]
        right = full[7:13]
        pat = self.PARITY_PATTERNS[first]
        binary = "101"
        for i, d in enumerate(left):
            binary += self.L_CODES[int(d)] if pat[i] == 'L' else self.G_CODES[int(d)]
        binary += "01010"
        for d in right:
            binary += self.R_CODES[int(d)]
        binary += "101"

        module_w = 3
        h = 100
        quiet = 30
        img_w = (len(binary) * module_w) + (2 * quiet)
        img = Image.new('RGB', (img_w, h + 50), 'white')
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("arial.ttf", 22)
        except:
            font = ImageFont.load_default()

        x = quiet
        for bit in binary:
            if bit == '1': draw.rectangle([x, 10, x + module_w - 1, h], fill='black')
            x += module_w

        draw.text((quiet - 20, h + 10), full[0], fill='black', font=font)
        draw.text((quiet + (3 * module_w) + 10, h + 10), full[1:7], fill='black', font=font)
        draw.text((quiet + (50 * module_w) + 10, h + 10), full[7:], fill='black', font=font)
        return img, full


class EAN13ManualDecoder:
    def __init__(self):
        gen = EAN13ManualGenerator()
        self.decode_L = {code: str(i) for i, code in enumerate(gen.L_CODES)}
        self.decode_G = {code: str(i) for i, code in enumerate(gen.G_CODES)}
        self.decode_R = {code: str(i) for i, code in enumerate(gen.R_CODES)}
        self.decode_parity = {pattern: str(i) for i, pattern in enumerate(gen.PARITY_PATTERNS)}

    def decode_image_file(self, filepath):
        img = Image.open(filepath).convert('L')
        width, height = img.size
        pixels = img.load()
        mid_y = height // 2


        raw_scan = [1 if pixels[x, mid_y] < 128 else 0 for x in range(width)]

        try:
            start_idx = raw_scan.index(1)
            end_idx = len(raw_scan) - 1 - raw_scan[::-1].index(1)
        except ValueError:
            raise ValueError("Штрих-код не знайдено")

        barcode_width = end_idx - start_idx + 1
        module_size = barcode_width / 95.0

        binary_string = ""
        for i in range(95):
            sample_x = start_idx + (i * module_size) + (module_size / 2)
            val = pixels[int(sample_x), mid_y]
            binary_string += '1' if val < 128 else '0'

        if binary_string[:3] != "101" or binary_string[-3:] != "101":
            raise ValueError("Нечіткі маркери")

        left_bin = binary_string[3:45]
        right_bin = binary_string[50:92]

        left_digits = ""
        parity_pat = ""

        for i in range(0, 42, 7):
            chunk = left_bin[i:i + 7]
            if chunk in self.decode_L:
                left_digits += self.decode_L[chunk]
                parity_pat += "L"
            elif chunk in self.decode_G:
                left_digits += self.decode_G[chunk]
                parity_pat += "G"
            else:

                return "Помилка читання (шум)"

        right_digits = ""
        for i in range(0, 42, 7):
            chunk = right_bin[i:i + 7]
            if chunk in self.decode_R:
                right_digits += self.decode_R[chunk]

        first_digit = self.decode_parity.get(parity_pat, "?")
        return first_digit + left_digits + right_digits


root = tk.Tk()
root.title("САІ: Комплекс Штрих-кодування")
root.geometry("600x650")

tab_control = ttk.Notebook(root)
tab1 = ttk.Frame(tab_control)
tab2 = ttk.Frame(tab_control)
tab3 = ttk.Frame(tab_control)

tab_control.add(tab1, text='Створення')
tab_control.add(tab2, text='Сканування')
tab_control.add(tab3, text='База Товарів')
tab_control.pack(expand=1, fill="both")


f_gen = tk.LabelFrame(tab1, text="Введення даних", padx=10, pady=10)
f_gen.pack(padx=20, pady=20, fill="x")

tk.Label(f_gen, text="Назва товару:").pack(anchor="w")
e_name = tk.Entry(f_gen)
e_name.pack(fill="x", pady=5)

tk.Label(f_gen, text="Код (12 цифр):").pack(anchor="w")
e_code = tk.Entry(f_gen)
e_code.pack(fill="x", pady=5)

lbl_preview = tk.Label(tab1)
lbl_preview.pack(pady=10)


def click_gen():
    name = e_name.get()
    raw_code = e_code.get()
    if not name or len(raw_code) != 12:
        messagebox.showerror("Помилка", "Перевірте назву та 12 цифр коду")
        return
    try:
        gen = EAN13ManualGenerator()
        img, full_code = gen.generate_image(raw_code)


        img_tk = ImageTk.PhotoImage(img)
        lbl_preview.config(image=img_tk)
        lbl_preview.image = img_tk


        filename = f"barcode_{full_code}.png"
        img.save(filename)


        if db_add_product(name, full_code):
            messagebox.showinfo("Успіх", f"Товар '{name}' збережено!\nКод: {full_code}")
            load_table_data()  # Оновити таблицю на 3-й вкладці

    except Exception as e:
        messagebox.showerror("Помилка", str(e))


tk.Button(f_gen, text="Згенерувати та Зберегти в БД", command=click_gen, bg="#dcedc8").pack(fill="x", pady=10)


f_scan = tk.LabelFrame(tab2, text="Декодування зображення", padx=10, pady=10)
f_scan.pack(padx=20, pady=20, fill="x")

lbl_scan_res = tk.Label(tab2, text="Результат з'явиться тут", font=("Arial", 12))
lbl_scan_res.pack(pady=20)


def click_scan():
    path = filedialog.askopenfilename()
    if not path: return
    try:
        decoder = EAN13ManualDecoder()
        decoded_code = decoder.decode_image_file(path)


        if "?" in decoded_code or len(decoded_code) != 13:
            lbl_scan_res.config(text=f"Не вдалося розпізнати: {decoded_code}", fg="red")
        else:

            db_info = db_find_product(decoded_code)
            lbl_scan_res.config(text=db_info, fg="blue")

    except Exception as e:
        lbl_scan_res.config(text=str(e), fg="red")


tk.Button(f_scan, text="Завантажити файл штрих-коду", command=click_scan, bg="#bbdefb").pack(fill="x", pady=10)


columns = ("id", "name", "code", "date")
tree = ttk.Treeview(tab3, columns=columns, show="headings")


tree.heading("id", text="ID")
tree.heading("name", text="Назва товару")
tree.heading("code", text="Штрих-код (EAN-13)")
tree.heading("date", text="Дата створення")


tree.column("id", width=50)
tree.column("name", width=200)
tree.column("code", width=120)
tree.column("date", width=150)

tree.pack(fill="both", expand=True, padx=10, pady=10)


def load_table_data():

    for row in tree.get_children():
        tree.delete(row)


    rows = db_get_all_products()


    for row in rows:

        formatted_row = list(row)
        if row[3]:  # Якщо дата є
            formatted_row[3] = row[3].strftime("%Y-%m-%d %H:%M")

        tree.insert("", "end", values=formatted_row)



btn_refresh = tk.Button(tab3, text="Оновити таблицю", command=load_table_data)
btn_refresh.pack(fill="x", padx=10, pady=5)


try:
    load_table_data()
except:
    pass

root.mainloop()