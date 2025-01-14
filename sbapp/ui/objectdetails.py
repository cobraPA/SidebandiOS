import time
import RNS

from kivy.metrics import dp,sp
from kivy.lang.builder import Builder
from kivy.core.clipboard import Clipboard
from kivy.utils import escape_markup
from kivymd.uix.recycleview import MDRecycleView
from kivymd.uix.list import OneLineIconListItem
from kivy.properties import StringProperty, BooleanProperty
from kivy.effects.scroll import ScrollEffect
from kivy.clock import Clock
from sideband.sense import Telemeter
import threading
import webbrowser

from kivymd.uix.button import MDRectangleFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.toast import toast

from datetime import datetime


if RNS.vendor.platformutils.get_platform() == "android":
    from ui.helpers import ts_format
else:
    from .helpers import ts_format

class ObjectDetails():
    def __init__(self, app, object_hash = None):
        self.app = app
        self.widget = None
        self.object_hash = object_hash
        self.lastest_timestamp = 0
        self.coords = None
        self.raw_telemetry = None
        self.from_telemetry = False
        self.from_conv = False
        self.viewing_self = False
        self.delete_dialog = None

        if not self.app.root.ids.screen_manager.has_screen("object_details_screen"):
            self.screen = Builder.load_string(layout_object_details)
            self.screen.app = self.app
            self.screen.delegate = self
            self.ids = self.screen.ids
            self.app.root.ids.screen_manager.add_widget(self.screen)

            self.screen.ids.object_details_container.effect_cls = ScrollEffect
            self.telemetry_list = RVDetails()
            self.telemetry_list.delegate = self
            self.telemetry_list.app = self.app
            self.screen.ids.object_details_container.add_widget(self.telemetry_list)

            ok_button = MDRectangleFlatButton(text="OK",font_size=dp(18))
            self.info_dialog = MDDialog(
                title="Info",
                text="",
                buttons=[ ok_button ],
            )

            def dl_ok(s):
                self.info_dialog.dismiss()
            ok_button.bind(on_release=dl_ok)

            Clock.schedule_interval(self.reload_job, 2)

    def reload_job(self, dt=None):
        if self.app.root.ids.screen_manager.current == "object_details_screen":
            latest_telemetry = self.app.sideband.peer_telemetry(self.object_hash, limit=1)
            if latest_telemetry != None and len(latest_telemetry) > 0:
                telemetry_timestamp = latest_telemetry[0][0]
                if telemetry_timestamp > self.lastest_timestamp:
                    self.reload_telemetry(notoast=True)

    def close_action(self, sender=None):
        if self.from_telemetry:
            self.app.telemetry_action(direction="right")
        else:
            if self.from_conv:
                self.app.open_conversation(self.object_hash, direction="right")
            else:
                self.app.close_sub_map_action()

    def confirm_delete_telemetry(self, sender=None):
        self.app.sideband.clear_telemetry(self.object_hash)

    def delete_telemetry_action(self, sender=None):
        if self.delete_dialog == None:
            yes_button = MDRectangleFlatButton(text="Yes",font_size=dp(18), theme_text_color="Custom", line_color=self.app.color_reject, text_color=self.app.color_reject)
            no_button = MDRectangleFlatButton(text="No",font_size=dp(18))
            self.delete_dialog = MDDialog(
                title="Clear telemetry?",
                text="This will permanently delete all collected telemetry for this object.",
                buttons=[ yes_button, no_button ],
            )
            def dl_yes(s):
                self.delete_dialog.dismiss()
                self.confirm_delete_telemetry()

                def cb(dt):
                    self.reload_telemetry(notoast=True)
                Clock.schedule_once(cb, 0.2)

            def dl_no(s):
                self.delete_dialog.dismiss()

            yes_button.bind(on_release=dl_yes)
            no_button.bind(on_release=dl_no)
        
        self.delete_dialog.open()

    def reload_telemetry(self, sender=None, notoast=False):
        if self.object_hash != None:
            self.set_source(self.object_hash, from_conv=self.from_conv, from_telemetry=self.from_telemetry)
            if not notoast:
                toast("Reloaded telemetry for object")

    def set_source(self, source_dest, from_conv=False, from_telemetry=False, prefetched=None):
        try:
            self.object_hash = source_dest
            own_address = self.app.sideband.lxmf_destination.hash
            telemetry_allowed = self.app.sideband.should_send_telemetry(source_dest)
            if source_dest == own_address:
                self.viewing_self = True
            else:
                self.viewing_self = False


            if from_telemetry:
                self.from_telemetry = True
            else:
                self.from_telemetry = False
                if from_conv:
                    self.from_conv = True
                else:
                    self.from_conv = False

            self.coords = None
            self.telemetry_list.data = []
            pds = self.app.sideband.peer_display_name(source_dest)
            appearance = self.app.sideband.peer_appearance(source_dest)
            self.screen.ids.name_label.text = pds

            if source_dest == own_address:
                self.screen.ids.name_label.text = pds+" (this device)"
            elif source_dest == self.app.sideband.config["telemetry_collector"]:
                self.screen.ids.name_label.text = pds+" (collector)"

            self.screen.ids.coordinates_button.disabled = True
            self.screen.ids.object_appearance.icon = appearance[0]
            self.screen.ids.object_appearance.icon_color = appearance[1]
            self.screen.ids.object_appearance.md_bg_color = appearance[2]
            def djob(dt):
                if self.viewing_self:
                    self.screen.ids.request_button.disabled = True
                    self.screen.ids.send_button.disabled = True
                else:
                    self.screen.ids.request_button.disabled = False
                    if telemetry_allowed:
                        self.screen.ids.send_button.disabled = False
                    else:
                        self.screen.ids.send_button.disabled = True

            if prefetched != None:
                latest_telemetry = prefetched
            else:
                latest_telemetry = self.app.sideband.peer_telemetry(source_dest, limit=1)

            if latest_telemetry != None and len(latest_telemetry) > 0:
                telemetry_timestamp = latest_telemetry[0][0]
                self.lastest_timestamp = telemetry_timestamp

                telemeter = Telemeter.from_packed(latest_telemetry[0][1])
                self.raw_telemetry = telemeter.read_all()

                relative_to = None
                if source_dest != own_address:
                    relative_to = self.app.sideband.telemeter

                rendered_telemetry = telemeter.render(relative_to=relative_to)
                if "location" in telemeter.sensors:
                    def job(dt):
                        self.screen.ids.coordinates_button.disabled = False
                    Clock.schedule_once(job, 0.01)
                    
                self.telemetry_list.update_source(rendered_telemetry)
                def job(dt):
                    self.screen.ids.telemetry_button.disabled = False
                Clock.schedule_once(job, 0.01)
            else:
                def job(dt):
                    self.screen.ids.telemetry_button.disabled = True
                Clock.schedule_once(job, 0.01)
                self.telemetry_list.update_source(None)

            self.telemetry_list.effect_cls = ScrollEffect
            Clock.schedule_once(djob, 0.1)
        except Exception as e:
            import traceback
            exception_info = "".join(traceback.TracebackException.from_exception(e).format())
            RNS.log(f"An {str(type(e))} occurred while updating service telemetry: {str(e)}", RNS.LOG_ERROR)
            RNS.log(exception_info, RNS.LOG_ERROR)

    def reload(self):
        self.clear_widget()
        self.update()

    def send_update(self):
        if not self.viewing_self:
            result = self.app.sideband.send_latest_telemetry(to_addr=self.object_hash)
            if result == "destination_unknown":
                title_str = "Unknown Destination"
                info_str  = "No keys known for the destination. Connected reticules have been queried for the keys."
            elif result == "in_progress":
                title_str = "Transfer In Progress"
                info_str  = "There is already an outbound telemetry transfer in progress for this peer."
            elif result == "already_sent":
                title_str = "Already Delivered"
                info_str  = "The current telemetry data was already sent and delivered to the peer or propagation network."
            elif result == "sent":
                title_str = "Update Sent"
                info_str  = "A telemetry update was sent to the peer."
            elif result == "not_sent":
                title_str = "Not Sent"
                info_str  = "A telemetry update could not be sent."
            else:
                title_str = "Unknown Status"
                info_str  = "The status of the telemetry update is unknown."
            
            self.info_dialog.title = title_str
            self.info_dialog.text  = info_str
            self.info_dialog.open()

    def request_update(self):
        if not self.viewing_self:
            result = self.app.sideband.request_latest_telemetry(from_addr=self.object_hash)

            if result == "destination_unknown":
                title_str = "Unknown Destination"
                info_str  = "No keys known for the destination. Connected reticules have been queried for the keys."
            elif result == "in_progress":
                title_str = "Transfer In Progress"
                info_str  = "There is already a telemetry request transfer in progress for this peer."
            elif result == "sent":
                title_str = "Request Sent"
                info_str  = "A telemetry request was sent to the peer. The peer should send any available telemetry shortly."
            elif result == "not_sent":
                title_str = "Not Sent"
                info_str  = "A telemetry request could not be sent."
            else:
                title_str = "Unknown Status"
                info_str  = "The status of the telemetry request is unknown."
            
            self.info_dialog.title = title_str
            self.info_dialog.text  = info_str
            self.info_dialog.open()

    def clear_widget(self):
        pass

    def update(self):
        us = time.time()
        self.update_widget()        
        RNS.log("Updated object details in "+RNS.prettytime(time.time()-us), RNS.LOG_DEBUG)

    def update_widget(self):
        if self.widget == None:
            self.widget = MDLabel(text=RNS.prettyhexrep(self.object_hash))

    def get_widget(self):
        return self.widget

    def copy_coordinates(self, sender=None):
        Clipboard.copy(str(self.coords or "No data"))

    def copy_telemetry(self, sender=None):
        Clipboard.copy(str(self.raw_telemetry or "No data"))

class ODView(OneLineIconListItem):
    icon = StringProperty()
    def __init__(self):
        super().__init__()

class RVDetails(MDRecycleView):
    def __init__(self):
        super().__init__()
        self.data = []

    def update_source(self, rendered_telemetry=None):
        try:
            if not rendered_telemetry:
                rendered_telemetry = []
            
            sort = {
                "Physical Link": 10,
                "Location": 20,
                "Ambient Light": 30,
                "Ambient Temperature": 40,
                "Relative Humidity": 50,
                "Ambient Pressure": 60,
                "Battery": 70,
                "Timestamp": 80,
                "Received": 90,
                "Information": 5,
            }
            self.entries = []
            rendered_telemetry.sort(key=lambda s: sort[s["name"]] if s["name"] in sort else 1000)
            for s in rendered_telemetry:
                extra_entries = []
                def pass_job(sender=None):
                    pass
                release_function = pass_job
                formatted_values = None
                name = s["name"]
                if name == "Timestamp":
                    ts = s["values"]["UTC"]
                    if ts != None:
                        ts_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                        formatted_values = f"Recorded [b]{RNS.prettytime(time.time()-ts, compact=True)} ago[/b] ({ts_str})"
                        def copy_info(e=None):
                            Clipboard.copy(ts_str)
                            toast("Copied to clipboard")
                        release_function = copy_info
                elif name == "Information":
                    info = s["values"]["contents"]
                    if info != None:
                        istr = str(info)
                        def copy_info(e=None):
                            Clipboard.copy(istr)
                            toast("Copied to clipboard")
                        release_function = copy_info
                        external_text = escape_markup(istr)
                        formatted_values = f"[b]Information[/b]: {external_text}"
                elif name == "Received":
                    formatted_values = ""
                    by = s["values"]["by"];
                    via = s["values"]["via"];

                    if by == self.app.sideband.lxmf_destination.hash:
                        if via == self.delegate.object_hash:
                            formatted_values = "Collected directly by [b]this device[/b], directly [b]from emitter[/b]"
                        else:
                            via_str = self.app.sideband.peer_display_name(via)
                            if via_str == None:
                                via_str = "an [b]unknown peer[/b]"
                            formatted_values = f"Collected directly by [b]this device[/b], via {via_str}"
                    else:
                        if via != None and via == by:
                            vstr = self.app.sideband.peer_display_name(via)
                            formatted_values = f"Received from, and collected by [b]{vstr}[/b]"
                        
                        else:
                            if via != None:
                                vstr = self.app.sideband.peer_display_name(via)
                                via_str = f"Received from [b]{vstr}[/b]"
                            else:
                                via_str = "Received from an [b]unknown peer[/b]"
                            
                            if by != None:
                                dstr = self.app.sideband.peer_display_name(by)
                                by_str = f", collected by [b]{dstr}[/b]"
                            else:
                                by_str = f", collected by an [b]unknown peer[/b]"

                            formatted_values = f"{via_str}{by_str}"

                    if formatted_values == "":
                        formatted_values = None

                    if not by == self.app.sideband.lxmf_destination.hash and not self.app.sideband.is_trusted(by):
                        extra_entries.append({"icon": "alert", "text": "Collected by a [b]non-trusted[/b] peer"})
                    
                elif name == "Battery":
                    p = s["values"]["percent"]
                    cs = s["values"]["_meta"]
                    if cs != None: cs_str = f" ({cs})"
                    if p != None: formatted_values = f"{name} [b]{p}%[/b]"+cs_str
                elif name == "Ambient Pressure":
                    p = s["values"]["mbar"]
                    if p != None: formatted_values = f"{name} [b]{p} mbar[/b]"
                    dt = "mbar"
                    if "deltas" in s and dt in s["deltas"] and s["deltas"][dt] != None:
                        d = s["deltas"][dt]
                        formatted_values += f"  (Δ = {d} mbar)"
                elif name == "Ambient Temperature":
                    c = s["values"]["c"]
                    if c != None: formatted_values = f"{name} [b]{c}° C[/b]"
                    dt = "c"
                    if "deltas" in s and dt in s["deltas"] and s["deltas"][dt] != None:
                        d = s["deltas"][dt]
                        formatted_values += f"  (Δ = {d}° C)"
                elif name == "Relative Humidity":
                    r = s["values"]["percent"]
                    if r != None: formatted_values = f"{name} [b]{r}%[/b]"
                    dt = "percent"
                    if "deltas" in s and dt in s["deltas"] and s["deltas"][dt] != None:
                        d = s["deltas"][dt]
                        formatted_values += f"  (Δ = {d}%)"
                elif name == "Physical Link":
                    rssi = s["values"]["rssi"]; rssi_str = None
                    snr = s["values"]["snr"]; snr_str = None
                    q = s["values"]["q"]; q_str = None
                    if q != None: q_str = f"Link Quality [b]{q}%[/b]"
                    if rssi != None:
                        rssi_str = f"RSSI [b]{rssi} dBm[/b]"
                        if q != None: rssi_str = ", "+rssi_str
                    if snr != None:
                        snr_str = f"SNR [b]{snr} dB[/b]"
                        if q != None or rssi != None: snr_str = ", "+snr_str
                    if q_str or rssi_str or snr_str:
                        formatted_values = q_str+rssi_str+snr_str
                elif name == "Location":
                    lat = s["values"]["latitude"]
                    lon = s["values"]["longitude"]
                    alt = s["values"]["altitude"]
                    speed = s["values"]["speed"]
                    heading = s["values"]["heading"]
                    accuracy = s["values"]["accuracy"]
                    updated = s["values"]["updated"]
                    updated_str = f", logged [b]{RNS.prettytime(time.time()-updated, compact=True)} ago[/b]"

                    coords = f"{lat}, {lon}"
                    fcoords = f"{round(lat,4)}, {round(lon,4)}"
                    self.delegate.coords = coords
                    if alt == 0:
                        alt_str = "0"
                    else:
                        alt_str = RNS.prettydistance(alt)
                    formatted_values = f"Coordinates [b]{fcoords}[/b], altitude [b]{alt_str}[/b]"
                    if speed != None:
                        if speed > 0.000001:
                            speed_formatted_values = f"Speed [b]{speed} Km/h[/b], heading [b]{heading}°[/b]"
                        else:
                            speed_formatted_values = f"Speed [b]0 Km/h[/b]"
                    else:
                        speed_formatted_values = None
                    extra_formatted_values = f"Uncertainty [b]{accuracy} meters[/b]"+updated_str

                    data = {"icon": s["icon"], "text": f"{formatted_values}"}

                    extra_entries.append({"icon": "map-marker-question", "text": extra_formatted_values})
                    if speed_formatted_values != None:
                        extra_entries.append({"icon": "speedometer", "text": speed_formatted_values})

                    if "distance" in s:
                        if "orthodromic" in s["distance"]:
                            od = s["distance"]["orthodromic"]
                            if od != None:
                                od_text = f"Geodesic distance [b]{RNS.prettydistance(od)}[/b]"
                                extra_entries.append({"icon": "earth", "text": od_text})
                        
                        if "euclidian" in s["distance"]:
                            ed = s["distance"]["euclidian"]
                            if ed != None:
                                ed_text = f"Euclidian distance [b]{RNS.prettydistance(ed)}[/b]"
                                extra_entries.append({"icon": "axis-arrow", "text": ed_text})
                        
                        if "vertical" in s["distance"]:
                            vd = s["distance"]["vertical"]
                            if vd != None:
                                if vd < 0:
                                    relstr = "lower"
                                    vd = abs(vd)
                                else:
                                    relstr = "greater"
                                vd_text = f"Altitude is [b]{RNS.prettydistance(vd)}[/b] {relstr} than this device"
                                extra_entries.append({"icon": "altimeter", "text": vd_text})

                    if "angle_to_horizon" in s["values"]:
                        oath = s["values"]["angle_to_horizon"]
                        if oath != None:
                            if self.delegate.viewing_self:
                                oath_text = f"Local horizon is at [b]{round(oath,3)}°[/b]"
                            else:
                                oath_text = f"Object's horizon is at [b]{round(oath,3)}°[/b]"
                            extra_entries.append({"icon": "arrow-split-horizontal", "text": oath_text})

                    if self.delegate.viewing_self and "radio_horizon" in s["values"]:
                        orh = s["values"]["radio_horizon"]
                        if orh != None:
                            range_text = RNS.prettydistance(orh)
                            rh_formatted_text = f"Radio horizon of [b]{range_text}[/b]"
                            extra_entries.append({"icon": "radio-tower", "text": rh_formatted_text})

                    if "azalt" in s and "local_angle_to_horizon" in s["azalt"]:
                        lath = s["azalt"]["local_angle_to_horizon"]
                        if lath != None:
                            lath_text = f"Local horizon is at [b]{round(lath,3)}°[/b]"
                            extra_entries.append({"icon": "align-vertical-distribute", "text": lath_text})

                    if "azalt" in s:
                        azalt_formatted_text = ""
                        if "azimuth" in s["azalt"]:
                            az = s["azalt"]["azimuth"]
                            az_text = f"Azimuth [b]{round(az,3)}°[/b]"
                            azalt_formatted_text += az_text
                        
                        if "altitude" in s["azalt"]:
                            al = s["azalt"]["altitude"]
                            al_text = f"altitude [b]{round(al,3)}°[/b]"
                            if len(azalt_formatted_text) != 0: azalt_formatted_text += ", "
                            azalt_formatted_text += al_text

                        extra_entries.append({"icon": "compass-rose", "text": azalt_formatted_text})

                        if "above_horizon" in s["azalt"]:
                            astr = "above" if s["azalt"]["above_horizon"] == True else "below"
                            dstr = str(round(s["azalt"]["altitude_delta"], 3))
                            ah_text = f"Object is [b]{astr}[/b] the horizon (Δ = {dstr}°)"
                            extra_entries.append({"icon": "angle-acute", "text": ah_text})

                    if not self.delegate.viewing_self and "radio_horizon" in s["values"]:
                        orh = s["values"]["radio_horizon"]
                        if orh != None:
                            range_text = RNS.prettydistance(orh)
                            rh_formatted_text = f"Object's radio horizon is [b]{range_text}[/b]"
                            extra_entries.append({"icon": "radio-tower", "text": rh_formatted_text})

                    if "radio_horizon" in s:
                        rh_icon = "circle-outline"
                        crange_text = RNS.prettydistance(s["radio_horizon"]["combined_range"])
                        if s["radio_horizon"]["within_range"]:
                            rh_formatted_text = f"[b]Within[/b] shared radio horizon of [b]{crange_text}[/b]"
                            rh_icon = "set-none"
                        else:
                            rh_formatted_text = f"[b]Outside[/b] shared radio horizon of [b]{crange_text}[/b]"
                        
                        extra_entries.append({"icon": rh_icon, "text": rh_formatted_text})

                    def select(e=None):
                        geo_uri = f"geo:{lat},{lon}"
                        def lj():
                            webbrowser.open(geo_uri)
                        threading.Thread(target=lj, daemon=True).start()

                    release_function = select
                else:
                    formatted_values = f"{name}"
                    for vn in s["values"]:
                        v = s["values"][vn]
                        formatted_values += f" [b]{v} {vn}[/b]"

                        dt = vn
                        if "deltas" in s and dt in s["deltas"] and s["deltas"][dt] != None:
                            d = s["deltas"][dt]
                            formatted_values += f"  (Δ = {d} {vn})"
                
                data = None
                if formatted_values != None:
                    if release_function:
                        data = {"icon": s["icon"], "text": f"{formatted_values}", "on_release": release_function}
                    else:
                        data = {"icon": s["icon"], "text": f"{formatted_values}"}

                if data != None:
                    self.entries.append(data)
                for extra in extra_entries:
                    self.entries.append(extra)

            if len(self.entries) == 0:
                self.entries.append({"icon": "timeline-question-outline", "text": f"No telemetry available for this device"})

            self.data = self.entries

        except Exception as e:
            import traceback
            exception_info = "".join(traceback.TracebackException.from_exception(e).format())
            RNS.log(f"An {str(type(e))} occurred while updating service telemetry: {str(e)}", RNS.LOG_ERROR)
            RNS.log(exception_info, RNS.LOG_ERROR)


layout_object_details = """
#:import MDLabel kivymd.uix.label.MDLabel
#:import OneLineIconListItem kivymd.uix.list.OneLineIconListItem
#:import Button kivy.uix.button.Button

<ODView>
    IconLeftWidget:
        icon: root.icon

<RVDetails>:
    viewclass: "ODView"
    effect_cls: "ScrollEffect"

    RecycleBoxLayout:
        default_size: None, dp(50)
        default_size_hint: 1, None
        size_hint_y: None
        height: self.minimum_height
        orientation: "vertical"

MDScreen:
    name: "object_details_screen"
    
    BoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            id: details_bar
            title: "Details"
            anchor_title: "left"
            elevation: 0
            left_action_items:
                [['menu', lambda x: root.app.nav_drawer.set_state("open")]]
            right_action_items:
                [
                ['map-search', lambda x: root.app.peer_show_location_action(root.delegate)],
                ['refresh', lambda x: root.delegate.reload_telemetry()],
                ['trash-can-outline', lambda x: root.delegate.delete_telemetry_action()],
                ['close', lambda x: root.delegate.close_action()],
                ]

        MDBoxLayout:
            id: object_header
            orientation: "horizontal"
            spacing: dp(24)
            size_hint_y: None
            height: self.minimum_height
            padding: dp(24)

            MDIconButton:
                id: object_appearance
                icon: "account-question"
                icon_color: [0,0,0,1]
                md_bg_color: [1,1,1,1]
                theme_icon_color: "Custom"
                icon_size: dp(32)
                on_release: root.app.converse_from_telemetry()

            MDLabel:
                id: name_label
                markup: True
                text: "Object Name"
                font_style: "H6"

        MDBoxLayout:
            orientation: "horizontal"
            spacing: dp(24)
            size_hint_y: None
            height: self.minimum_height
            padding: [dp(24), dp(0), dp(24), dp(24)]

            MDRectangleFlatIconButton:
                id: telemetry_button
                icon: "content-copy"
                text: "Copy Telemetry"
                padding: [dp(0), dp(14), dp(0), dp(14)]
                icon_size: dp(24)
                font_size: dp(16)
                size_hint: [1.0, None]
                on_release: root.delegate.copy_telemetry(self)
                disabled: False

            MDRectangleFlatIconButton:
                id: coordinates_button
                icon: "map-marker-outline"
                text: "Copy Coordinates"
                padding: [dp(0), dp(14), dp(0), dp(14)]
                icon_size: dp(24)
                font_size: dp(16)
                size_hint: [1.0, None]
                on_release: root.delegate.copy_coordinates(self)
                disabled: False
                
        MDSeparator:
            orientation: "horizontal"
            height: dp(1)

        MDBoxLayout:
            orientation: "vertical"
            id: object_details_container
                
        MDSeparator:
            orientation: "horizontal"
            height: dp(1)

        MDBoxLayout:
            orientation: "horizontal"
            spacing: dp(24)
            size_hint_y: None
            height: self.minimum_height
            padding: [dp(24), dp(24), dp(24), dp(24)]

            MDRectangleFlatIconButton:
                id: send_button
                icon: "upload-lock"
                text: "Send Update"
                padding: [dp(0), dp(14), dp(0), dp(14)]
                icon_size: dp(24)
                font_size: dp(16)
                size_hint: [1.0, None]
                on_release: root.delegate.send_update()
                disabled: False

            MDRectangleFlatIconButton:
                id: request_button
                icon: "arrow-down-bold-hexagon-outline"
                text: "Request Update"
                padding: [dp(0), dp(14), dp(0), dp(14)]
                icon_size: dp(24)
                font_size: dp(16)
                size_hint: [1.0, None]
                on_release: root.delegate.request_update()
                disabled: False

        # MDBoxLayout:
        #     orientation: "horizontal"
        #     spacing: dp(16)
        #     size_hint_y: None
        #     height: self.minimum_height
        #     padding: [dp(24), dp(16), dp(24), dp(24)]

        #     MDRectangleFlatIconButton:
        #         id: delete_button
        #         icon: "trash-can-outline"
        #         text: "Delete All Telemetry"
        #         padding: [dp(0), dp(14), dp(0), dp(14)]
        #         icon_size: dp(24)
        #         font_size: dp(16)
        #         size_hint: [1.0, None]
        #         on_release: root.delegate.copy_telemetry(self)
        #         disabled: False
                
"""