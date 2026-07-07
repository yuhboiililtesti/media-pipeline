"""Type definitions for the discovery engine."""
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Movie:
    tmdb_id: int
    title: str
    year: int
    confidence: float = 0.0
    reason: str = ""
    genres: list[str] = field(default_factory=list)
    added_to_radarr: bool = False

@dataclass 
class TasteProfile:
    user: str
    genres: dict[str, float] = field(default_factory=dict)
    actors: dict[str, float] = field(default_factory=dict)
    directors: dict[str, float] = field(default_factory=dict)
    
    def score_genre(self, genre: str) -> float:
        return self.genres.get(genre, 0.0)
    
    def score_actor(self, actor: str) -> float:
        return self.actors.get(actor, 0.0)
    
    def score_director(self, director: str) -> float:
        return self.directors.get(director, 0.0)
