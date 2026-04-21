import asyncio
import logging
import time
import importlib.util
import os
from typing import Dict, Optional, Any, List

logger = logging.getLogger('neon.sim_controller')

class SimulationController:
    """
    Manages running simulation sessions on the server.
    Ensures simulations/scenarios 'run' on the server autonomously.
    """
    def __init__(self):
        self.sessions = {}
        self.placeables = {} # session_id -> List of placeable objects
        self.is_running = False
        self._ticker_task = None

    def add_session(self, session_id: str, session: Any):
        self.sessions[session_id] = session
        scenario_data = None
        if hasattr(session, '_mutator') and hasattr(session._mutator, 'scenario_data'):
            scenario_data = session._mutator.scenario_data
        elif hasattr(session, 'scenario_data'):
            scenario_data = session.scenario_data
        
        if scenario_data and 'placeables' in scenario_data:
             self.placeables[session_id] = self._instantiate_placeables(scenario_data['placeables'])
        else:
             self.placeables[session_id] = []
        
        logger.info(f'Session {session_id} added to controller with {len(self.placeables.get(session_id, []))} placeables.')

    def _instantiate_placeables(self, configs: List[Dict[str, Any]]) -> List[Any]:
        objs = []
        for cfg in configs:
            try:
                p_id = cfg['id']
                p_type = cfg['type']
                x = cfg.get('x_km', 0)
                y = cfg.get('y_km', 0)
                props = cfg.get('properties', {})
                
                cls = self._load_placeable_class(p_type)
                obj = cls(p_id, p_type, x, y, props)
                objs.append(obj)
            except Exception as e:
                logger.error(f'Failed to instantiate placeable {cfg}: {e}')
        return objs

    def _load_placeable_class(self, type_name: str):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, 'placeables', f'{type_name}.py')
        if not os.path.exists(path):
            path = os.path.join(base_dir, 'placeables', 'template.py')
        
        # Set up a qualified name and package context to support relative imports in placeables
        qualified_name = f"placeables.{type_name}"
        spec = importlib.util.spec_from_file_location(qualified_name, path)
        if spec is None or spec.loader is None:
             from placeables.base import PlaceableBase
             return PlaceableBase

        module = importlib.util.module_from_spec(spec)
        module.__package__ = "placeables"
        spec.loader.exec_module(module)
        return getattr(module, 'Template')

    def remove_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]
        if session_id in self.placeables:
            del self.placeables[session_id]
        logger.info(f'Session {session_id} removed')

    def update_placeables(self, session_id: str, configs: List[Dict[str, Any]]):
        self.placeables[session_id] = self._instantiate_placeables(configs)
        logger.info(f'Session {session_id} placeables updated. Count: {len(self.placeables[session_id])}')

    def start(self):
        if not self.is_running:
            self.is_running = True
            self._ticker_task = asyncio.create_task(self._run_ticker())
            logger.info('Simulation Controller started')

    def stop(self):
        self.is_running = False
        if self._ticker_task:
            self._ticker_task.cancel()
        logger.info('Simulation Controller stopped')

    async def _run_ticker(self):
        tick = 0
        while self.is_running:
            start_time = time.time()
            
            for session_id, session in list(self.sessions.items()):
                playing = True
                if hasattr(session, 'is_playing'):
                    playing = session.is_playing
                elif hasattr(session, '_playing'):
                    playing = session._playing
                
                if not playing:
                    continue
                
                p_list = self.placeables.get(session_id, [])
                if p_list:
                    world_state = {
                        'placeables': {p.id: p.to_dict() for p in p_list},
                    }
                    if hasattr(session, 'get_state_snapshot'):
                        snap = session.get_state_snapshot()
                        world_state['tracks'] = snap.get('tracks', [])
                        world_state['assets'] = snap.get('assets', [])
                    
                    for p in p_list:
                        try:
                            p.step(tick, world_state)
                        except Exception as e:
                            logger.error(f'Error in placeable {p.id} step: {e}')
                    
                    for p in p_list:
                        if p.id in world_state['placeables']:
                             d = world_state['placeables'][p.id].get('data')
                             if d is not None: p.data = d
                             p.x_km = world_state['placeables'][p.id].get('x_km', p.x_km)
                             p.y_km = world_state['placeables'][p.id].get('y_km', p.y_km)

            tick += 1
            elapsed = time.time() - start_time
            sleep_time = max(0.01, 1.0 - elapsed)
            try:
                await asyncio.sleep(sleep_time)
            except asyncio.CancelledError:
                break

    def get_session(self, session_id: str) -> Optional[Any]:
        return self.sessions.get(session_id)
