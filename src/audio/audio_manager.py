import flet as ft
import flet_audio as fta
import time
from typing import Optional

from utilities.values import clamp

class AudioManager:
    """Handles all Flet-based audio playbacks with culling and cooldowns."""
    def __init__(
        self,
        page: ft.Page, *,
        music_volume: float = 0.3,
        sfx_volume: float = 0.5,
        directional_sfx: bool = True,
        debug: bool = False,
    ) -> None:
        self.page = page
        self.debug = debug
        
        # Performance & Logic tracking
        self._music_volume = music_volume
        self._sfx_volume = sfx_volume
        self.directional_sfx = directional_sfx
        self._sfx_cooldowns: dict[str, float] = {}
        self._sfx_instances: list[fta.Audio] = []
        self.music_instance: Optional[fta.Audio] = None
    
    @property
    def sfx_volume(self) -> float:
        return self._sfx_volume
    
    @sfx_volume.setter
    def sfx_volume(self, volume: float) -> None:
        new_vol = round(clamp(volume), 2)
        self._sfx_volume = new_vol
        self._debug_msg(f"Setting SFX volume to: {new_vol}")
        if len(self._sfx_instances) > 0:
            for sfx in self._sfx_instances:
                sfx.volume = new_vol
                sfx.update()
    
    @property
    def music_volume(self) -> float:
        return self._music_volume
    
    @music_volume.setter
    def music_volume(self, volume: float) -> None:
        new_vol = round(clamp(volume), 2)
        self._music_volume = new_vol
        self._debug_msg(f"Setting Music volume to: {new_vol}")
        if self.music_instance:
            self.music_instance.volume = new_vol
            self.music_instance.update()
            
    def _debug_msg(self, msg: str) -> None:
        if self.debug: print(f"[AudioManager] {msg}")
        
    def play_music(self, music_src: str) -> None:
        """Plays music on a loop. Replaces current music if it exists."""
        try:
            if self.music_instance is None:
                self._debug_msg(f"Playing music: {music_src}")
                self.music_instance = fta.Audio(
                    src=music_src,
                    autoplay=True,
                    volume=self.music_volume,
                    release_mode=fta.ReleaseMode.LOOP
                )
            else:
                if self.music_instance.src == music_src:
                    self.page.run_task(self.music_instance.play)
                else:
                    self.music_instance.src = music_src
                    self.music_instance.update()
        except Exception as e:
            self._debug_msg(f"Music Error: {e}")
            
    def play_sfx(
        self, sfx_src: str,
        left_volume: float = None,
        right_volume: float = None,
        base_volume: float = None
    ) -> None:
        """Plays a sound effect with panning and spam prevention."""
        try:
            # Distance Culling
            if self.directional_sfx and left_volume is not None and right_volume is not None:
                if left_volume < 0.01 and right_volume < 0.01: return
                
            # Spam Prevention (50ms Cooldown)
            curr_time: float = time.time()
            if curr_time - self._sfx_cooldowns.get(sfx_src, 0) < 0.05: return
            self._sfx_cooldowns[sfx_src] = curr_time
            
            # Calculate Balance (Panning)
            # Flet Balance: -1.0 (Left) to 1.0 (Right)
            calc_balance: float = 0.0
            if left_volume is not None and right_volume is not None:
                calc_balance = clamp(right_volume - left_volume, -1.0, 1.0)
                
            final_vol = self.sfx_volume if base_volume is None else clamp(base_volume) * self.sfx_volume
            
            # Create 'Fire and Forget' instance with auto-cleanup
            def on_state_change(e: fta.AudioStateChangeEvent):
                if e.state == fta.AudioState.COMPLETED:
                    # print(f"SFX Instances: {len(self._sfx_instances)}")
                    self.page.run_task(new_sfx.release) # Frees underlying platform resources
                    self._sfx_instances.remove(new_sfx)
                    # print(f"SFX Instances: {len(self._sfx_instances)}")
            
            self._debug_msg(f"Playing SFX: {sfx_src}")
            new_sfx = fta.Audio(
                src=sfx_src,
                volume=final_vol,
                balance=calc_balance,
                autoplay=True,
                on_state_change=on_state_change
            )
            self._sfx_instances.append(new_sfx)
            
        except Exception as e:
            self._debug_msg(f"SFX Error: {e}")