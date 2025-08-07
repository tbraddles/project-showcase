# Project Texas

A Python-based simulator for Texas Hold’em Poker designed to model gameplay mechanics and support strategy testing. The project emphasizes object-oriented design principles and logic-driven simulation of betting rounds and player actions.

## Overview

The goal of Project Texas is to build a flexible and extensible poker engine that simulates realistic gameplay — from pre-flop through showdown — to support future development of automated strategy agents and statistical analysis.

## Key Components

- **Game Engine**:
  - Object-oriented architecture representing players, cards, hands, and the game state.
  - Functional simulation of full hand progression: deal, betting rounds, community cards, and winner evaluation.
  
- **Gameplay Logic**:
  - Turn-based action sequencing.
  - Betting logic with pot tracking and basic fold/call/raise decisions.
  - Internal hand evaluator for showdown comparisons.

## Files Included

- `texas_simulator.py`: Core simulation file containing object-oriented implementation of the game loop and player interactions.

## Skills Demonstrated

- Python (OOP design, control flow, modularisation)
- Simulation logic and turn-based state management
- Game rule implementation
- Planning for extensibility and future features

## Future Improvements

- Error handling for invalid states and inputs
- Support for edge-case scenarios (e.g., side pots logic)
- Integration of basic AI agents for decision-making
- UI or CLI enhancements for user interaction

## Status

🛠️ In progress — core gameplay logic functional; work ongoing on improving realism, edge case handling, and extensibility.

---

*This project is part of a broader portfolio submitted for software engineering internship applications.*
