import os
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
from PIL import Image, ImageTk

# URL de l'API PhotoRoom (pour détourage)
PHOTOROOM_ENDPOINT = "https://sdk.photoroom.com/v1/segment"

# Nouveau Thème "Futuriste 2025"
THEME = {
    # Couleurs de fond principales
    'primary':      '#1B1C1E',   # gris très foncé (presque noir)
    'secondary':    '#1B1C1E',   # gris foncé pour les sections

    # Couleurs d'accent
    'accent':       '#104774',   # violet néon
    'button':       '#104774',   # même teinte que l'accent
    'button_text':  '#FFFFFF',   # texte clair sur bouton
    'button_hover': '#0b69a3',   # violet plus clair au survol

    # Texte
    'text':         '#F1F1F1',   # texte clair
    'input_bg':     '#2E2E31',   # champ de saisie sombre
    'input_text':   '#F5F5F5',   # texte plus clair dans les champs

    # Bordure / success / error
    'border':       '#104774',   # même violet
    'success':      '#33DB96',   # vert vif
    'error':        '#FF4D4D',   # rouge vif
    'warning':      '#FFC107'    # jaune d’avertissement
}

PADDING = 20
ENTRY_WIDTH = 50

class FuturisticPhotoRoomApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PhotoRoom Studio - Edition 2025")
        self.root.configure(bg=THEME['primary'])
        # Empêche le redimensionnement :
        self.root.resizable(False, False)

        # Nom du fichier texte pour stocker la clé
        self.api_key_path = "photoroom_api_key.txt"

        # Configuration du style ttk
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.setup_styles()

        # Queues de communication
        self.queue_detourage = queue.Queue()
        self.queue_logo = queue.Queue()

        # Flags annulation
        self.cancel_requested_detourage = False
        self.cancel_requested_logo = False

        # Conteneur principal
        self.main_container = ttk.Frame(self.root, style='Main.TFrame')
        self.main_container.pack(fill='both', expand=True, padx=PADDING, pady=PADDING)

        # Notebook (avec deux onglets)
        self.notebook = ttk.Notebook(self.main_container, style='Card.TNotebook')
        self.notebook.pack(fill='both', expand=True)

        # Création des onglets
        self.setup_detourage_tab()
        self.setup_logo_tab()

        # Charge la clé API si elle existe
        self.load_api_key_if_exists()

        # Polling des queues
        self.root.after(200, self.check_detourage_queue)
        self.root.after(200, self.check_logo_queue)

        # Image de prévisualisation
        self.preview_image_ref = None

        # Taille minimale
        self.root.minsize(900, 700)
        # Centre la fenêtre
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f'+{x}+{y}')

    def setup_styles(self):
        """
        Définit les styles ttk avec un design “futuriste 2025”.
        """
        # Cadre principal
        self.style.configure('Main.TFrame', background=THEME['primary'])

        # Cadre secondaire (style "Card")
        self.style.configure('Card.TFrame',
                             background=THEME['secondary'],
                             relief='flat',
                             borderwidth=0)

        # Police “futuriste” : on peut utiliser “Helvetica”, “Roboto”, etc.
        base_font = ('Roboto', 10)

        # Labels
        self.style.configure('Futura.TLabel',
                             background=THEME['secondary'],
                             foreground=THEME['text'],
                             font=base_font,
                             padding=5)

        # Titre de section
        self.style.configure('Header.TLabel',
                             background=THEME['secondary'],
                             foreground=THEME['text'],
                             font=('Roboto', 14, 'bold'),
                             padding=10)

        # Boutons
        self.style.configure('Futura.TButton',
                             background=THEME['button'],
                             foreground=THEME['button_text'],
                             padding=(20, 10),
                             font=('Roboto', 10, 'bold'),
                             borderwidth=0)

        self.style.map('Futura.TButton',
                       background=[('active', THEME['button_hover'])])

        # Entries
        self.style.configure('Futura.TEntry',
                             fieldbackground=THEME['input_bg'],
                             foreground=THEME['input_text'],
                             padding=10,
                             borderwidth=0,
                             font=base_font)

        # Notebook (onglets)
        self.style.configure('Card.TNotebook',
                             background=THEME['primary'],
                             borderwidth=0)

        self.style.configure('Card.TNotebook.Tab',
                             background=THEME['secondary'],
                             foreground=THEME['text'],
                             padding=[30, 15],
                             font=('Roboto', 11, 'bold'),
                             borderwidth=0)

        self.style.map('Card.TNotebook.Tab',
                       background=[('selected', THEME['accent'])],
                       foreground=[('selected', THEME['text'])])

        # ProgressBar
        self.style.configure('Futura.Horizontal.TProgressbar',
                             troughcolor=THEME['accent'],
                             bordercolor=THEME['border'],
                             background=THEME['text'],
                             thickness=4)

    def create_section_frame(self, parent, title):
        """
        Crée un cadre (style 'Card.TFrame') avec un label "Header"
        si title n'est pas vide.
        """
        frame = ttk.Frame(parent, style='Card.TFrame')
        frame.pack(fill='x', pady=(0, 20), padx=20, ipadx=20, ipady=20)
        if title:
            ttk.Label(frame, text=title.upper(), style='Header.TLabel').pack(fill='x', pady=(0, 15))
        return frame

    # ----------------------------------------------------------------------------------
    #                               Onglet 1 : Détourage
    # ----------------------------------------------------------------------------------
    def setup_detourage_tab(self):
        self.frame_detourage = ttk.Frame(self.notebook, style='Main.TFrame')
        self.notebook.add(self.frame_detourage, text=" SUPPRESSION DE L'ARRIÈRE-PLAN ")

        # --- Section : API Key ---
        api_frame = self.create_section_frame(self.frame_detourage, "API Configuration")

        ttk.Label(api_frame, text="PhotoRoom API Key", style='Futura.TLabel').pack(fill='x')

        api_line = ttk.Frame(api_frame, style='Card.TFrame')
        api_line.pack(fill='x')

        self.entry_api_key = ttk.Entry(api_line, width=ENTRY_WIDTH, style='Futura.TEntry')
        self.entry_api_key.pack(side='left', fill='x', expand=True)

        ttk.Button(api_line, text="Clé de sauvegarde",
                   style='Futura.TButton',
                   command=self.save_api_key).pack(side='left', padx=5)

        ttk.Button(api_line, text="Effacer la clé",
                   style='Futura.TButton',
                   command=self.clear_api_key).pack(side='left')

        # --- Section : Input / Output ---
        io_frame = self.create_section_frame(self.frame_detourage, "Entrée et sortie")

        input_container = ttk.Frame(io_frame, style='Card.TFrame')
        input_container.pack(fill='x', pady=(0, 15))

        ttk.Label(input_container, text="Dossier d'entrée", style='Futura.TLabel').pack(side='left')
        self.entry_detourage_in = ttk.Entry(input_container, width=ENTRY_WIDTH, style='Futura.TEntry')
        self.entry_detourage_in.pack(side='left', padx=10)
        ttk.Button(input_container, text="Parcourir",
                   style='Futura.TButton',
                   command=self.choisir_dossier_detourage).pack(side='left')

        output_container = ttk.Frame(io_frame, style='Card.TFrame')
        output_container.pack(fill='x')

        ttk.Label(output_container, text="Dossier de sortie", style='Futura.TLabel').pack(side='left')
        self.entry_detourage_out = ttk.Entry(output_container, width=ENTRY_WIDTH, style='Futura.TEntry')
        self.entry_detourage_out.pack(side='left', padx=10)
        ttk.Button(output_container, text="Parcourir",
                   style='Futura.TButton',
                   command=self.choisir_dossier_sortie_detourage).pack(side='left')

        # --- Section : Progress & Buttons ---
        progress_frame = self.create_section_frame(self.frame_detourage, "Progress")

        self.progress_detourage = ttk.Progressbar(progress_frame,
                                                  orient='horizontal',
                                                  length=400,
                                                  mode='determinate',
                                                  style='Futura.Horizontal.TProgressbar')
        self.progress_detourage.pack(fill='x', pady=(0, 15))

        button_container = ttk.Frame(progress_frame, style='Card.TFrame')
        button_container.pack(fill='x')

        ttk.Button(button_container,
                   text="START",
                   command=self.start_detourage_thread,
                   style='Futura.TButton').pack(side='left', padx=(0, 10))

        ttk.Button(button_container,
                   text="CANCEL",
                   command=self.cancel_detourage,
                   style='Futura.TButton').pack(side='left')

    # ----------------------------------------------------------------------------------
    #                               Onglet 2 : Logo & Resize
    # ----------------------------------------------------------------------------------
    def setup_logo_tab(self):
        self.frame_logo = ttk.Frame(self.notebook, style='Main.TFrame')
        self.notebook.add(self.frame_logo, text=" redimensionner d'image ")

        # --- Section : Logo Configuration ---
        logo_frame = self.create_section_frame(self.frame_logo, "Logo Configuration")

        logo_container = ttk.Frame(logo_frame, style='Card.TFrame')
        logo_container.pack(fill='x', pady=(0, 15))

        ttk.Label(logo_container, text="Fichier du logo", style='Futura.TLabel').pack(side='left')
        self.entry_logo = ttk.Entry(logo_container, width=ENTRY_WIDTH, style='Futura.TEntry')
        self.entry_logo.pack(side='left', padx=10)
        ttk.Button(logo_container, text="Browse",
                   style='Futura.TButton',
                   command=self.choisir_logo).pack(side='left')

        # Hauteur (offset)
        height_container = ttk.Frame(logo_frame, style='Card.TFrame')
        height_container.pack(fill='x')

        ttk.Label(height_container, text="Hauteur du logo (px)", style='Futura.TLabel').pack(side='left')
        self.entry_espace_bas = ttk.Entry(height_container, width=10, style='Futura.TEntry')
        self.entry_espace_bas.insert(0, "-100")
        self.entry_espace_bas.pack(side='left', padx=10)

        # --- Section : Input & Output ---
        io_frame = self.create_section_frame(self.frame_logo, "Entrée et sortie")

        input_container = ttk.Frame(io_frame, style='Card.TFrame')
        input_container.pack(fill='x', pady=(0, 15))

        ttk.Label(input_container, text="Dossier d'images", style='Futura.TLabel').pack(side='left')
        self.entry_images = ttk.Entry(input_container, width=ENTRY_WIDTH, style='Futura.TEntry')
        self.entry_images.pack(side='left', padx=10)
        ttk.Button(input_container, text="Browse",
                   style='Futura.TButton',
                   command=self.choisir_dossier_images).pack(side='left')

        output_container = ttk.Frame(io_frame, style='Card.TFrame')
        output_container.pack(fill='x')

        ttk.Label(output_container, text="Dossier de sortie", style='Futura.TLabel').pack(side='left')
        self.entry_sortie = ttk.Entry(output_container, width=ENTRY_WIDTH, style='Futura.TEntry')
        self.entry_sortie.pack(side='left', padx=10)
        ttk.Button(output_container, text="Browse",
                   style='Futura.TButton',
                   command=self.choisir_dossier_sortie).pack(side='left')

        # --- Section : Progress & Buttons ---
        progress_frame = self.create_section_frame(self.frame_logo, "Progress")

        self.progress_logo = ttk.Progressbar(progress_frame,
                                             orient='horizontal',
                                             length=400,
                                             mode='determinate',
                                             style='Futura.Horizontal.TProgressbar')
        self.progress_logo.pack(fill='x', pady=(0, 15))

        button_container = ttk.Frame(progress_frame, style='Card.TFrame')
        button_container.pack(fill='x')

        ttk.Button(button_container,
                   text="Prévisualiser l'image",
                   command=self.preview_logo,
                   style='Futura.TButton').pack(side='left', padx=(0, 10))

        ttk.Button(button_container,
                   text="START",
                   command=self.start_logo_thread,
                   style='Futura.TButton').pack(side='left', padx=(0, 10))

        ttk.Button(button_container,
                   text="CANCEL",
                   command=self.cancel_logo,
                   style='Futura.TButton').pack(side='left')

    # ----------------------------------------------------------------------------------
    #               Gestion de la clé API PhotoRoom (Load/Save/Clear)
    # ----------------------------------------------------------------------------------
    def load_api_key_if_exists(self):
        if os.path.isfile(self.api_key_path):
            try:
                with open(self.api_key_path, 'r', encoding='utf-8') as f:
                    saved_key = f.read().strip()
                if saved_key:
                    self.entry_api_key.insert(0, saved_key)
            except:
                pass

    def save_api_key(self):
        current_key = self.entry_api_key.get().strip()
        if not current_key:
            messagebox.showwarning("Warning", "API Key is empty. Enter a key before saving.")
            return
        try:
            with open(self.api_key_path, 'w', encoding='utf-8') as f:
                f.write(current_key)
            messagebox.showinfo("Info", "API Key saved successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save API Key: {e}")

    def clear_api_key(self):
        self.entry_api_key.delete(0, tk.END)
        if os.path.isfile(self.api_key_path):
            try:
                os.remove(self.api_key_path)
                messagebox.showinfo("Info", "API Key has been cleared.")
            except Exception as e:
                messagebox.showerror("Error", f"Could not remove API Key file: {e}")

    # ----------------------------------------------------------------------------------
    #                    Méthodes "Browse" (choix dossiers/fichiers)
    # ----------------------------------------------------------------------------------
    def choisir_dossier_detourage(self):
        d = filedialog.askdirectory(title="Select input folder for detourage")
        if d:
            self.entry_detourage_in.delete(0, tk.END)
            self.entry_detourage_in.insert(0, d)

    def choisir_dossier_sortie_detourage(self):
        d = filedialog.askdirectory(title="Select output folder for detourage")
        if d:
            self.entry_detourage_out.delete(0, tk.END)
            self.entry_detourage_out.insert(0, d)

    def choisir_logo(self):
        f = filedialog.askopenfilename(title="Select logo file",
                                       filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.webp")])
        if f:
            self.entry_logo.delete(0, tk.END)
            self.entry_logo.insert(0, f)

    def choisir_dossier_images(self):
        d = filedialog.askdirectory(title="Select input folder for images")
        if d:
            self.entry_images.delete(0, tk.END)
            self.entry_images.insert(0, d)

    def choisir_dossier_sortie(self):
        d = filedialog.askdirectory(title="Select output folder")
        if d:
            self.entry_sortie.delete(0, tk.END)
            self.entry_sortie.insert(0, d)

    # ----------------------------------------------------------------------------------
    #                      Détourage PhotoRoom (Thread + Queue)
    # ----------------------------------------------------------------------------------
    def start_detourage_thread(self):
        self.cancel_requested_detourage = False
        api_key = self.entry_api_key.get().strip()
        in_folder = self.entry_detourage_in.get().strip()
        out_folder = self.entry_detourage_out.get().strip()

        t = threading.Thread(target=self._detourage_thread_func,
                             args=(api_key, in_folder, out_folder))
        t.start()

    def _detourage_thread_func(self, api_key, input_folder, output_folder):
        if not api_key:
            self.queue_detourage.put(("ERROR", "Veuillez saisir votre clé API PhotoRoom"))
            return
        if not os.path.isdir(input_folder):
            self.queue_detourage.put(("ERROR", "Veuillez sélectionner un dossier d'entrée valide"))
            return
        if not os.path.exists(output_folder):
            os.makedirs(output_folder, exist_ok=True)

        image_paths = []
        for root_dir, _, files in os.walk(input_folder):
            for file_name in files:
                if file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                    image_paths.append(os.path.join(root_dir, file_name))

        total = len(image_paths)
        if total == 0:
            self.queue_detourage.put(("INFO", "No images to process."))
            return

        self.queue_detourage.put(("START", total))

        processed = 0
        for img_path in image_paths:
            if self.cancel_requested_detourage:
                self.queue_detourage.put(("CANCELED", None))
                return
            try:
                self._process_detourage(img_path, api_key, input_folder, output_folder)
            except Exception as e:
                self.queue_detourage.put(("MSG", f"Error processing {img_path}: {e}"))
            processed += 1
            self.queue_detourage.put(("PROGRESS", processed))

        self.queue_detourage.put(("DONE", None))

    def _process_detourage(self, img_path, api_key, input_folder, output_folder):
        with open(img_path, 'rb') as f:
            files = {"image_file": f}
            headers = {"x-api-key": api_key}
            r = requests.post(PHOTOROOM_ENDPOINT, headers=headers, files=files)

        if r.status_code == 200:
            root_dir = os.path.dirname(img_path)
            file_name = os.path.basename(img_path)
            relative_path = os.path.relpath(root_dir, input_folder)
            out_dir = os.path.join(output_folder, relative_path)
            os.makedirs(out_dir, exist_ok=True)
            output_path = os.path.join(out_dir, file_name)
            with open(output_path, 'wb') as w:
                w.write(r.content)
        else:
            raise Exception(f"API error: {r.status_code}")

    def check_detourage_queue(self):
        try:
            while True:
                msg, data = self.queue_detourage.get_nowait()
                if msg == "ERROR":
                    messagebox.showerror("Error", data)
                elif msg == "INFO":
                    messagebox.showinfo("Info", data)
                elif msg == "START":
                    self.progress_detourage["maximum"] = data
                    self.progress_detourage["value"] = 0
                elif msg == "PROGRESS":
                    self.progress_detourage["value"] = data
                elif msg == "MSG":
                    print("[Detourage]", data)
                elif msg == "CANCELED":
                    messagebox.showwarning("Canceled", "Processing was canceled.")
                elif msg == "DONE":
                    messagebox.showinfo("Success", "Processing completed successfully.")
        except queue.Empty:
            pass

        self.root.after(200, self.check_detourage_queue)

    def cancel_detourage(self):
        self.cancel_requested_detourage = True

    # ----------------------------------------------------------------------------------
    #              Redimension + Logo (Thread + Queue) + Preview
    # ----------------------------------------------------------------------------------
    def start_logo_thread(self):
        self.cancel_requested_logo = False
        logo_path = self.entry_logo.get().strip()
        in_folder = self.entry_images.get().strip()
        out_folder = self.entry_sortie.get().strip()

        try:
            espace_bas = int(self.entry_espace_bas.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Logo height must be an integer.")
            return

        t = threading.Thread(target=self._logo_thread_func,
                             args=(logo_path, in_folder, out_folder, espace_bas))
        t.start()

    def _logo_thread_func(self, logo_path, in_folder, out_folder, espace_bas):
        if not os.path.isfile(logo_path):
            self.queue_logo.put(("ERROR", "Veuillez sélectionner un fichier de logo valide"))
            return
        if not os.path.isdir(in_folder):
            self.queue_logo.put(("ERROR", "Veuillez sélectionner un dossier d'entrée valide"))
            return
        if not os.path.exists(out_folder):
            os.makedirs(out_folder, exist_ok=True)

        try:
            logo = Image.open(logo_path).convert("RGBA")
        except Exception as e:
            self.queue_logo.put(("ERROR", f"Cannot open logo file: {e}"))
            return

        image_paths = []
        for root_dir, _, files in os.walk(in_folder):
            for f in files:
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                    image_paths.append(os.path.join(root_dir, f))

        total = len(image_paths)
        if total == 0:
            self.queue_logo.put(("INFO", "No images to process."))
            return

        self.queue_logo.put(("START", total))

        processed = 0
        for img_path in image_paths:
            if self.cancel_requested_logo:
                self.queue_logo.put(("CANCELED", None))
                return
            try:
                self._process_logo(img_path, logo, in_folder, out_folder, espace_bas)
            except Exception as e:
                self.queue_logo.put(("MSG", f"Error processing {img_path}: {e}"))
            processed += 1
            self.queue_logo.put(("PROGRESS", processed))

        self.queue_logo.put(("DONE", None))

    def _process_logo(self, img_path, logo, in_folder, out_folder, espace_bas):
        """
        Redimensionne l'image si nécessaire (max 1000 px sur le côté le plus long),
        puis la place au centre d'un canevas 1000x1000 en réservant de l'espace en bas (espace_bas).
        Enfin, colle le logo en bas du canevas.
        """
        file_name = os.path.basename(img_path)
        root_dir = os.path.dirname(img_path)
        relative_path = os.path.relpath(root_dir, in_folder)
        out_dir = os.path.join(out_folder, relative_path)
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, file_name)

        with Image.open(img_path).convert("RGBA") as image:
            w, h = image.size
            max_dim = max(w, h)

            # === MODIFICATIONS ICI: on passe le max à 1000, au lieu de 690 ===
            if max_dim > 1000:
                ratio = 1000 / max_dim
            else:
                ratio = 1.0

            new_size = (int(w * ratio), int(h * ratio))
            resized = image.resize(new_size, Image.Resampling.LANCZOS)

            # Centrage dans un canevas 1000x1000
            rw, rh = resized.size
            left_margin = (1000 - rw) // 2

            # On réserve espace_bas en bas (pour le logo), puis on centre verticalement
            remaining_space = 1000 - rh - espace_bas
            top_margin = remaining_space // 2

            canvas = Image.new("RGBA", (1000, 1000), (255, 255, 255, 255))
            canvas.paste(resized, (left_margin, top_margin), resized)

            # Collage du logo en bas (ex: y = 1000 - logo_height - 15)
            lw, lh = logo.size
            logo_x = (1000 - lw) // 2
            logo_y = 1000 - lh - 15
            canvas.paste(logo, (logo_x, logo_y), logo)

            # Convertir en RGB si format JPEG
            if file_name.lower().endswith(('.jpg', '.jpeg')):
                canvas = canvas.convert("RGB")

            canvas.save(output_path)

    def check_logo_queue(self):
        try:
            while True:
                msg, data = self.queue_logo.get_nowait()
                if msg == "ERROR":
                    messagebox.showerror("Error", data)
                elif msg == "INFO":
                    messagebox.showinfo("Info", data)
                elif msg == "START":
                    self.progress_logo["maximum"] = data
                    self.progress_logo["value"] = 0
                elif msg == "PROGRESS":
                    self.progress_logo["value"] = data
                elif msg == "MSG":
                    print("[Logo]", data)
                elif msg == "CANCELED":
                    messagebox.showwarning("Canceled", "Processing was canceled.")
                elif msg == "DONE":
                    messagebox.showinfo("Success", "Processing completed successfully.")
        except queue.Empty:
            pass
        self.root.after(200, self.check_logo_queue)

    def cancel_logo(self):
        self.cancel_requested_logo = True

    # ----------------------------------------------------------------------------------
    #                          Prévisualisation d'une image
    # ----------------------------------------------------------------------------------
    def preview_logo(self):
        logo_path = self.entry_logo.get().strip()
        folder_in = self.entry_images.get().strip()
        try:
            espace_bas = int(self.entry_espace_bas.get().strip())
        except ValueError:
            messagebox.showerror("Error", "La hauteur du logo doit être un entier")
            return

        if not os.path.isfile(logo_path):
            messagebox.showerror("Error", "Veuillez sélectionner un fichier de logo valide")
            return

        if not os.path.isdir(folder_in):
            messagebox.showerror("Error", "Veuillez sélectionner un dossier d'entrée valide")
            return

        preview_path = filedialog.askopenfilename(
            title="Choose an image for preview",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.webp")],
            initialdir=folder_in
        )
        if not preview_path:
            return

        try:
            logo_img = Image.open(logo_path).convert("RGBA")
            with Image.open(preview_path).convert("RGBA") as source_img:
                preview_result = self._process_image_preview(source_img, logo_img, espace_bas)
            self.show_preview_window(preview_result, preview_path)
        except Exception as e:
            messagebox.showerror("Error", f"Preview generation failed: {e}")

    def _process_image_preview(self, image_rgba, logo_rgba, espace_bas):
        """
        Même logique que _process_logo mais en mode "preview".
        On applique le redimensionnement max 1000 px, et on centre l’image
        sur un canevas 1000×1000, puis on colle le logo.
        """
        w, h = image_rgba.size
        max_dim = max(w, h)

        # === MODIFICATIONS ICI: on passe le max à 1000, au lieu de 690 ===
        if max_dim > 1000:
            ratio = 1000 / max_dim
        else:
            ratio = 1.0

        new_size = (int(w * ratio), int(h * ratio))
        resized = image_rgba.resize(new_size, Image.Resampling.LANCZOS)

        rw, rh = resized.size
        left_margin = (1000 - rw) // 2

        remaining_space = 1000 - rh - espace_bas
        top_margin = remaining_space // 2

        canvas = Image.new("RGBA", (1000, 1000), (255, 255, 255, 255))
        canvas.paste(resized, (left_margin, top_margin), resized)

        lw, lh = logo_rgba.size
        logo_x = (1000 - lw) // 2
        logo_y = 1000 - lh - 15
        canvas.paste(logo_rgba, (logo_x, logo_y), logo_rgba)

        return canvas

    def show_preview_window(self, pil_image, image_path):
        preview_win = tk.Toplevel(self.root)
        preview_win.title(f"Preview: {os.path.basename(image_path)}")
        preview_win.configure(bg=THEME['primary'])

        self.preview_image_ref = ImageTk.PhotoImage(pil_image)
        lbl = tk.Label(preview_win, image=self.preview_image_ref, bg=THEME['primary'])
        lbl.pack(padx=10, pady=10)

        ttk.Button(preview_win, text="Close Preview",
                   style='Futura.TButton',
                   command=preview_win.destroy).pack(pady=(0, 20))

        preview_win.update_idletasks()
        w = preview_win.winfo_width()
        h = preview_win.winfo_height()
        x = (preview_win.winfo_screenwidth() // 2) - (w // 2)
        y = (preview_win.winfo_screenheight() // 2) - (h // 2)
        preview_win.geometry(f"{w}x{h}+{x}+{y}")

def main():
    root = tk.Tk()
    app = FuturisticPhotoRoomApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
