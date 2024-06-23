from warshard.map import Hexagon, HexGrid, Map
from warshard.actions import Fight
from warshard.config import Config


class Unit:

    def __init__(
        self, hexagon_position: Hexagon, type: str, player_side, id, parent_map: Map
    ) -> None:

        self.parent_map = parent_map

        assert type in Config.UNIT_CHARACTERISTICS.keys()
        self.type: str = type  # armor, hq, etc.

        self.player_side = player_side

        stats = Config.UNIT_CHARACTERISTICS[self.type]
        self.power, self.defense, self.mobility, self.range = stats

        self.hexagon_position: Hexagon = hexagon_position
        self.mobility_remaining = 0

        self.id = id  # Unique ID crucial for selection # TODO assert that the id always matches the g.map.all_units[27], ie. the key in the dictionary ? Or permit differences ? I think we should assert it.
        # TODO also assert that ID is an integer between 1 and 99 included

        self.involved_in_fight = None  # type : <Fight or None>

    def force_move_to(self, hex: Hexagon):
        # TODO used for retreats
        # (and debug in general)
        self.hexagon_position = hex

    def attempt_move_to(self, hex: Hexagon):
        # Check that we are trying to move into an ADJACENT HEX
        # TODO need to write very explicitly in the doc that, for now, if you want to move
        # more than 1 hex per turn you simply need to QUEUE movement orders
        if HexGrid.manhattan_distance_hex_grid(self.hexagon_position, hex) > 1:
            return

        # check if enough mobility remaining to move there, and if not occupied (using parent_map.is_accessible_to_player_side(self.player_side))
        mobility_cost = Config.MOBILITY_COSTS[hex.type]
        hex_is_clear, hex_not_in_enemy_zoc = hex.is_accessible_to_player_side(
            self.player_side
        )

        if (mobility_cost <= self.mobility_remaining) and hex_is_clear:
            # substract mobility cost of target hex to our remaining_mobility
            self.mobility_remaining -= mobility_cost
            self.force_move_to(hex)  # move there

            # if in enemy zoc, set remaining mobility to 0
            if not hex_not_in_enemy_zoc:
                self.mobility_remaining = 0

    def attempt_attack_on_hex(self, hex):
        # Check we are not already involved in a fight
        if self.involved_in_fight is not None:
            return

        # Check if we are within range of target hex
        distance = HexGrid.manhattan_distance_hex_grid(self.hexagon_position, hex)
        if distance > self.range:
            return

        # Check if the target hex contains an enemy unit
        target_hex_contains_enemy_unit = False
        for unit_id, unit in self.parent_map.all_units.items():
            if unit.player_side != self.player_side and unit.hexagon_position == hex:
                target_hex_contains_enemy_unit = True
                current_occupier = unit
                break
        if not target_hex_contains_enemy_unit:
            return

        # If self.parent_map.all_fights does not have a fight on this hex, create it before we attempty to join it :
        if hex not in self.parent_map.ongoing_fights:
            # Create a fight and add it to the list
            # Add the enemy unit present on this hex as the melee defender
            this_fight = Fight(defending_melee_unit=current_occupier)
            self.parent_map.ongoing_fights[hex] = this_fight

        # In any case, either the fight was created or we found an existing one, now join it as attacker!
        this_fight = self.parent_map.ongoing_fights[hex]
        this_fight.attacking_units.append(self)
        self.involved_in_fight = this_fight

    def attempt_join_defense_on_hex(self, hex):
        # Check we are not already involved in a fight
        if self.involved_in_fight is not None:
            return

        # Check we are not a melee unit
        if self.type in Config.MELEE_UNITS:
            return

        # Check we are within range to join
        distance = HexGrid.manhattan_distance_hex_grid(self.hexagon_position, hex)
        if distance > self.range:
            return

        # Check a fight exists at destination
        if hex in self.parent_map.ongoing_fights:
            # Join the fight as support
            this_fight = self.parent_map.ongoing_fights[hex]
            this_fight.defending_support_units.append(self)
            self.involved_in_fight = this_fight
