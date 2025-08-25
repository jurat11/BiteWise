from .start import register_start_handlers
from .water import register_water_handlers
from .meal import register_meal_handlers
from .stats import register_stats_handlers
from .settings import register_settings_handlers
from .help import register_help_handlers

__all__ = [
    'register_start_handlers',
    'register_water_handlers',
    'register_meal_handlers',
    'register_stats_handlers',
    'register_settings_handlers',
    'register_help_handlers'
] 