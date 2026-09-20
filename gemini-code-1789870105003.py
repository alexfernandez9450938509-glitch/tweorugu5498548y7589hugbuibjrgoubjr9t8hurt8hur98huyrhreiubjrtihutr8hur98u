import requests
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.clock import mainthread
import threading

class DNSLogApp(App):
    def build(self):
        self.server_url = ""
        self.main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Top Bar with Title and Action Buttons
        top_bar = BoxLayout(size_hint_y=None, height=50, spacing=10)
        title_label = Label(text="DNS Logs", font_size='20sp', bold=True, halign='left')
        
        # Change IP button
        ip_btn = Button(text="IP Config", size_hint_x=None, width=100, background_color=(0.5, 0.5, 0.5, 1))
        ip_btn.bind(on_release=lambda instance: self.prompt_for_ip())

        # Refresh button
        refresh_btn = Button(text="Refresh", size_hint_x=None, width=90, background_color=(0.2, 0.6, 1, 1))
        refresh_btn.bind(on_release=self.refresh_logs)

        top_bar.add_widget(title_label)
        top_bar.add_widget(ip_btn)
        top_bar.add_widget(refresh_btn)
        self.main_layout.add_widget(top_bar)

        # Scrollable list for logs
        self.scroll_view = ScrollView()
        self.log_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        self.log_list.bind(minimum_height=self.log_list.setter('height'))
        self.scroll_view.add_widget(self.log_list)
        
        self.main_layout.add_widget(self.scroll_view)

        return self.main_layout

    def on_start(self):
        # Automatically trigger the server IP prompt when the app launches on iOS
        self.prompt_for_ip()

    def prompt_for_ip(self):
        # Load previously saved IP if it exists in local storage
        saved_ip = self.config.getdefault('Network', 'server_ip', '')

        content = BoxLayout(orientation='vertical', padding=15, spacing=10)
        
        instructions = Label(
            text="Enter DNS Server IP / Address:\n(e.g., 192.168.1.50 or 192.168.1.50:5000)",
            halign='center',
            size_hint_y=None,
            height=40
        )
        
        self.ip_input = TextInput(
            text=saved_ip,
            multiline=False,
            font_size='18sp',
            size_hint_y=None,
            height=45,
            padding_y=[10, 10]
        )
        
        btn_layout = BoxLayout(size_hint_y=None, height=45, spacing=10)
        connect_btn = Button(text="Connect & Load", background_color=(0.2, 0.8, 0.2, 1))
        
        btn_layout.add_widget(connect_btn)
        
        content.add_widget(instructions)
        content.add_widget(self.ip_input)
        content.add_widget(btn_layout)

        self.ip_popup = Popup(
            title="Configure Server Connection",
            content=content,
            size_hint=(0.9, 0.45),
            auto_dismiss=False
        )

        connect_btn.bind(on_release=self.save_ip_and_connect)
        self.ip_popup.open()

    def save_ip_and_connect(self, instance):
        raw_ip = self.ip_input.text.strip()
        if not raw_ip:
            return

        # Automatically format protocol and port 5000 if user omitted it
        if not raw_ip.startswith("http://") and not raw_ip.startswith("https://"):
            raw_ip = "http://" + raw_ip
        
        if ":" not in raw_ip.replace("http://", "").replace("https://", ""):
            raw_ip = raw_ip + ":5000"

        self.server_url = f"{raw_ip}/api/logs"

        # Save to persistent storage on the iOS device
        self.config.set('Network', 'server_ip', self.ip_input.text.strip())
        self.config.write()

        self.ip_popup.dismiss()
        self.refresh_logs()

    def build_config(self, config):
        config.setdefaults('Network', {'server_ip': ''})

    def refresh_logs(self, instance=None):
        if not self.server_url:
            self.prompt_for_ip()
            return
        threading.Thread(target=self.fetch_data_from_server, daemon=True).start()

    def fetch_data_from_server(self):
        try:
            response = requests.get(self.server_url, timeout=5)
            if response.status_code == 200:
                logs = response.json()
                self.update_ui_logs(logs)
        except Exception as e:
            self.show_error_popup(str(e))

    @mainthread
    def show_error_popup(self, error_msg):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        lbl = Label(text=f"Connection Failed:\n{error_msg}\n\nCheck your server IP and try again.")
        retry_btn = Button(text="Change IP", size_hint_y=None, height=40)
        content.add_widget(lbl)
        content.add_widget(retry_btn)

        err_popup = Popup(title="Error", content=content, size_hint=(0.8, 0.4))
        retry_btn.bind(on_release=lambda x: (err_popup.dismiss(), self.prompt_for_ip()))
        err_popup.open()

    @mainthread
    def update_ui_logs(self, logs):
        self.log_list.clear_widgets()

        for entry in logs:
            btn_text = f"{entry['domain']}\n[{entry['timestamp']}]"
            item_btn = Button(
                text=btn_text, 
                size_hint_y=None, 
                height=55, 
                halign='left',
                valign='center',
                padding=(10, 5),
                background_color=(0.15, 0.15, 0.18, 1)
            )
            item_btn.bind(size=item_btn.setter('text_size'))
            item_btn.bind(on_release=lambda btn, data=entry: self.show_details_popup(data))
            self.log_list.add_widget(item_btn)

    def show_details_popup(self, log_data):
        content = BoxLayout(orientation='vertical', padding=15, spacing=10)
        
        details_text = (
            f"[b]Domain Requested:[/b]\n{log_data['domain']}\n\n"
            f"[b]Connected Device IP:[/b]\n{log_data['ip']}\n\n"
            f"[b]Device Hostname:[/b]\n{log_data['device_name']}\n\n"
            f"[b]Connection Timestamp:[/b]\n{log_data['timestamp']}"
        )
        
        info_label = Label(text=details_text, markup=True, halign='left', valign='top')
        info_label.bind(size=info_label.setter('text_size'))
        
        close_btn = Button(text="Close", size_hint_y=None, height=40)
        content.add_widget(info_label)
        content.add_widget(close_btn)

        popup = Popup(
            title="Connection Details",
            content=content,
            size_hint=(0.85, 0.6)
        )
        close_btn.bind(on_release=popup.dismiss)
        popup.open()

if __name__ == '__main__':
    DNSLogApp().run()