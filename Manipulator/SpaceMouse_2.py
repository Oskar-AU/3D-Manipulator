from Manipulator.Driver_Interface.IO import Datagrams
from Manipulator.Driver_Interface import Motion_Commands


class LinUDPClient:
    def __init__(self, host, port, master_id=1, sub_id=0):
        self.host = host
        self.port = port
        self.master_id = master_id
        self.sub_id = sub_id
        self.cmd_count_bit = 0  # toggles each motion command
        self.datagram = Datagrams.linUDP(host=self.host, port=self.port)

    def _next_count(self):
        self.cmd_count_bit ^= 1
        return self.cmd_count_bit

    def start_pva_stream(self, pos_mm, vel_mms, acc_mms2):
        count = self._next_count()
        # Build the PVA stream start command
        cmd = Motion_Commands.PVA_Stream_Start(
            axis=0, pos=pos_mm, vel=vel_mms, acc=acc_mms2,
            master_id=self.master_id, sub_id=self.sub_id, cmd_count=count
        )
        # Send the command
        self.datagram.send(cmd.get_binary(count))

    def continue_pva_stream(self, pos_mm, vel_mms, acc_mms2):
        count = self._next_count()
        cmd = Motion_Commands.PVA_Stream_Continue(
            axis=0, pos=pos_mm, vel=vel_mms, acc=acc_mms2,
            master_id=self.master_id, sub_id=self.sub_id, cmd_count=count
        )
        self.datagram.send(cmd.get_binary(count))

    def stop_stream(self):
        count = self._next_count()
        cmd = Motion_Commands.Stop_Stream(
            axis=0,
            master_id=self.master_id, sub_id=self.sub_id, cmd_count=count
        )
        self.datagram.send(cmd.get_binary(count))

    def read_status(self):
        # Optionally implement status polling if needed
        return {}

# ...rest of your SpaceMouse_2.py unchanged...
# ---- SpaceMouse wrapper (replace with your actual lib) ----
class SpaceMouse:
    def open(self):  # HOOK
        pass
    def close(self): # HOOK
        pass
    def read(self):
        """
        Return a dict like:
        {"axes": (x, y, z, rx, ry, rz), "buttons": [b0, b1, ...]}
        Raw units consistent with your lib.
        """
        return {"axes": (0,0,0,0,0,0), "buttons": [False, False]}

# ====== Controller ======
class SpaceMouseLinMotController:
    def __init__(self, linudp: LinUDPClient, spm: SpaceMouse, initial_pos_mm=0.0):
        self.linudp = linudp
        self.spm = spm
        self.state = AxisState(pos=initial_pos_mm, vel=0.0)
        self.dt = 1.0 / HZ
        self.streaming = False

    def _axes_to_vel(self, axes):
        # Map SpaceMouse Z (axes[2]) to velocity
        raw = _apply_deadzone(axes[2], DEADZONE)
        shaped = _shape(raw / 350.0, VEL_CURVE_P)  # normalize ~[-1,1] then curve
        v_cmd = shaped * VEL_GAIN * 350.0         # back to mm/s scale
        return _clamp(v_cmd, -V_MAX, V_MAX)

    def _compute_acc(self, v_new, v_old):
        a = (v_new - v_old) / self.dt
        return _clamp(a, -A_MAX, A_MAX)

    def _integrate_pos(self, pos, v):
        p = pos + v * self.dt
        return _clamp(p, POS_MIN, POS_MAX)

    def _deadman(self, buttons):
        try:
            return bool(buttons[DEADMAN_BUTTON])
        except Exception:
            return False

    def start(self):
        self.spm.open()
        try:
            # idle until deadman pressed once
            while True:
                io = self.spm.read()
                if self._deadman(io["buttons"]):
                    # prime stream with current state
                    acc0 = 0.0
                    self.linudp.start_pva_stream(self.state.pos, 0.0, acc0)
                    self.streaming = True
                    break
                time.sleep(0.01)

            # main loop
            next_t = time.perf_counter()
            while True:
                # maintain loop timing
                next_t += self.dt
                io = self.spm.read()

                if not self._deadman(io["buttons"]):
                    if self.streaming:
                        self.linudp.stop_stream()
                        self.streaming = False
                    # stay idle until deadman re-pressed
                    time.sleep(max(0.0, next_t - time.perf_counter()))
                    continue

                v_cmd = self._axes_to_vel(io["axes"])
                a_cmd = self._compute_acc(v_cmd, self.state.vel)
                p_cmd = self._integrate_pos(self.state.pos, v_cmd)

                # Update internal state (mirror what we send)
                self.state.pos = p_cmd
                self.state.vel = v_cmd

                # Optional: check status/warnings
                st = self.linudp.read_status()
                if st.get("error"):
                    # break or attempt safe stop
                    if self.streaming:
                        self.linudp.stop_stream()
                        self.streaming = False
                    break

                # Send next sample
                if not self.streaming:
                    self.linudp.start_pva_stream(p_cmd, v_cmd, a_cmd)
                    self.streaming = True
                else:
                    self.linudp.continue_pva_stream(p_cmd, v_cmd, a_cmd)

                # sleep to keep cadence
                time.sleep(max(0.0, next_t - time.perf_counter()))
        finally:
            # ensure stream is stopped on exit
            try:
                if self.streaming:
                    self.linudp.stop_stream()
            except Exception:
                pass
            self.spm.close()

# ====== Example wiring ======
if __name__ == "__main__":
    lin = LinUDPClient(host="192.168.0.10", port=502)
    spm = SpaceMouse()
    ctrl = SpaceMouseLinMotController(lin, spm, initial_pos_mm=10.0)
    ctrl.start()