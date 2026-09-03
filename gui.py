import argparse
import json
import socket
import customtkinter as ctk

CTRL_HOST = "127.0.0.1"
DEFAULT_CTRL_PORT = 5005

# Configure modern appearance settings
ctk.set_appearance_mode("System")  # Options: "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # Options: "blue", "dark-blue", "green"


def send_position(port, deg_lat, min_lat, hemi_lat, deg_lon, min_lon, hemi_lon):
    """Send a new position to the GPS feed server."""
    message = {
        "deg_lat": deg_lat,
        "min_lat": min_lat,
        "hemi_lat": hemi_lat,
        "deg_lon": deg_lon,
        "min_lon": min_lon,
        "hemi_lon": hemi_lon,
    }

    with socket.create_connection((CTRL_HOST, port), timeout=2) as sock:
        sock.sendall(json.dumps(message).encode("utf-8"))
        response = sock.recv(4096).decode("utf-8")

    if response != "OK":
        raise RuntimeError(response)


class ModernGPSGui(ctk.CTk):
    def __init__(self, ctrl_port):
        super().__init__()

        self.ctrl_port = ctrl_port

        # Window setup
        self.title("Fake GPS Feed")
        self.geometry("460x360")
        self.resizable(False, False)

        # Layout configuration
        self.grid_columnconfigure(0, weight=1)

        # Container Frame
        self.main_frame = ctk.CTkFrame(self, corner_radius=12)
        self.main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Title
        self.lbl_header = ctk.CTkLabel(
            self.main_frame,
            text="GPS Feed Controller",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.lbl_header.grid(row=0, column=0, columnspan=3, padx=15, pady=(15, 10))

        # --- Latitude Controls ---
        self.lbl_lat = ctk.CTkLabel(
            self.main_frame, text="Latitude", font=ctk.CTkFont(size=13, weight="bold")
        )
        self.lbl_lat.grid(row=1, column=0, columnspan=3, padx=15, pady=(5, 2), sticky="w")

        self.entry_lat_deg = ctk.CTkEntry(self.main_frame, placeholder_text="50", width=60)
        self.entry_lat_deg.insert(0, "50")
        self.entry_lat_deg.grid(row=2, column=0, padx=(15, 5), pady=5)

        self.combo_lat_hemi = ctk.CTkOptionMenu(
            self.main_frame, values=["N", "S"], width=70
        )
        self.combo_lat_hemi.set("N")
        self.combo_lat_hemi.grid(row=2, column=1, padx=5, pady=5)

        self.entry_lat_min = ctk.CTkEntry(
            self.main_frame, placeholder_text="00.0000", width=110
        )
        self.entry_lat_min.insert(0, "00.0000")
        self.entry_lat_min.grid(row=2, column=2, padx=(5, 15), pady=5)

        # --- Longitude Controls ---
        self.lbl_lon = ctk.CTkLabel(
            self.main_frame, text="Longitude", font=ctk.CTkFont(size=13, weight="bold")
        )
        self.lbl_lon.grid(row=3, column=0, columnspan=3, padx=15, pady=(10, 2), sticky="w")

        self.entry_lon_deg = ctk.CTkEntry(self.main_frame, placeholder_text="000", width=60)
        self.entry_lon_deg.insert(0, "000")
        self.entry_lon_deg.grid(row=4, column=0, padx=(15, 5), pady=5)

        self.combo_lon_hemi = ctk.CTkOptionMenu(
            self.main_frame, values=["E", "W"], width=70
        )
        self.combo_lon_hemi.set("E")
        self.combo_lon_hemi.grid(row=4, column=1, padx=5, pady=5)

        self.entry_lon_min = ctk.CTkEntry(
            self.main_frame, placeholder_text="00.0000", width=110
        )
        self.entry_lon_min.insert(0, "00.0000")
        self.entry_lon_min.grid(row=4, column=2, padx=(5, 15), pady=5)

        # --- Buttons ---
        self.btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.btn_frame.grid(row=5, column=0, columnspan=3, padx=15, pady=15)

        self.btn_apply = ctk.CTkButton(
            self.btn_frame, text="Apply", command=self.on_apply, width=110
        )
        self.btn_apply.pack(side="left", padx=5)

        self.btn_quit = ctk.CTkButton(
            self.btn_frame,
            text="Quit",
            command=self.destroy,
            fg_color="#D32F2F",
            hover_color="#B71C1C",
            width=110,
        )
        self.btn_quit.pack(side="left", padx=5)

        # --- Status Bar ---
        self.lbl_status = ctk.CTkLabel(
            self.main_frame,
            text=f"Connected to GPS server on 127.0.0.1:{self.ctrl_port}",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            wraplength=380,
        )
        self.lbl_status.grid(row=6, column=0, columnspan=3, padx=15, pady=(0, 15))

        # Bind enter key to Apply button action
        self.bind("<Return>", lambda event: self.on_apply())

    def on_apply(self):
        try:
            deg_lat = int(self.entry_lat_deg.get())
            min_lat = float(self.entry_lat_min.get())
            hemi_lat = self.combo_lat_hemi.get()

            deg_lon = int(self.entry_lon_deg.get())
            min_lon = float(self.entry_lon_min.get())
            hemi_lon = self.combo_lon_hemi.get()

            if not 0 <= min_lat < 60:
                raise ValueError("Latitude minutes must be between 0 and 60.")

            if not 0 <= min_lon < 60:
                raise ValueError("Longitude minutes must be between 0 and 60.")

            if not 0 <= deg_lat <= 90:
                raise ValueError("Invalid latitude degrees.")

            if not 0 <= deg_lon <= 180:
                raise ValueError("Invalid longitude degrees.")

            send_position(
                self.ctrl_port,
                deg_lat,
                min_lat,
                hemi_lat,
                deg_lon,
                min_lon,
                hemi_lon,
            )

            self.lbl_status.configure(
                text=f"Updated: {deg_lat:02d}°{min_lat:07.4f}{hemi_lat}  "
                f"{deg_lon:03d}°{min_lon:07.4f}{hemi_lon}",
                text_color=("black", "white"),
            )

        except ValueError as e:
            self.lbl_status.configure(text=f"Invalid position: {e}", text_color="#E53935")

        except (ConnectionError, OSError) as e:
            self.lbl_status.configure(
                text=f"Could not connect to GPS server: {e}", text_color="#E53935"
            )

        except RuntimeError as e:
            self.lbl_status.configure(text=f"Server error: {e}", text_color="#E53935")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--ctrl-port",
        type=int,
        default=DEFAULT_CTRL_PORT,
        help="server control socket port (default: 5005)",
    )
    args = ap.parse_args()

    app = ModernGPSGui(ctrl_port=args.ctrl_port)
    app.mainloop()


if __name__ == "__main__":
    main()