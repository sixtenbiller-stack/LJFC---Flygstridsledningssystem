import asyncio
import logging
import time
from typing import Dict, Optional, Any
from scenario_runtime import LiveSession

logger = logging.getLogger("neon.sim_controller")

class SimulationController:
    """
    Manages running simulation sessions on the server.
    Ensures simulations/scenarios 'run' on the server autonomously.
    """
    def __init__(self):
        self.sessions: Dict[str, Any] = {}
        self._ticker_task: Optional[asyncio.Task] = None
        self._last_tick = time.monotonic()

    def add_session(self, session_id: str, session: Any):
        self.sessions[session_id] = session
        if not self._ticker_task:
            self.start()

    def remove_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]
        if not self.sessions and self._ticker_task:
            self.stop()

    def start(self):
        if self._ticker_task:
            return
        self._ticker_task = asyncio.create_task(self._run_ticker())
        logger.info("Simulation Controller ticker started")

    def stop(self):
        if self._ticker_task:
            self._ticker_task.cancel()
            self._ticker_task = None
            logger.info("Simulation Controller ticker stopped")

    async def _run_ticker(self):
        while True:
            try:
                now = time.monotonic()
                dt = now - self._last_tick
                self._last_tick = now
                
                # Tick all active and playing sessions
                for session_id, session in list(self.sessions.items()):
                    if hasattr(session, 'is_playing') and session.is_playing:
                        # If it is a LiveSession or similar
                        if hasattr(session, 'tick'):
                            # We pass None to tick() to use the controller's dt
                            # but LiveSession.tick uses its own wall-clock if dt is None
                            # so we pass dt to be precise
                            session.tick(dt_s=dt * getattr(session, '_speed', 1.0))
                
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in Simulation Controller ticker")
                await asyncio.sleep(1.0)

    def get_session(self, session_id: str) -> Optional[Any]:
        return self.sessions.get(session_id)
