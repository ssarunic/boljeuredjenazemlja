"""MCP Prompts - Reusable templates for common workflows."""

import logging
from typing import Any

from cadastral_api import CadastralAPIClient
from cadastral_api.exceptions import CadastralAPIError

from .config import config

logger = logging.getLogger(__name__)


class CadastralPrompts:
    """
    MCP Prompts for cadastral queries.

    Prompts are reusable, parameterized message templates that users
    can explicitly invoke (like slash commands) to standardize
    interactions with the AI.
    """

    def __init__(self, client: CadastralAPIClient) -> None:
        """Initialize prompts with a cadastral API client."""
        self.client = client

    async def explain_ownership_structure(self, parcel_id: str) -> str:
        """
        Generate a prompt to explain parcel ownership structure.

        Args:
            parcel_id: The unique parcel identifier

        Returns:
            Formatted prompt text with ownership data for AI analysis
        """
        try:
            logger.info(f"Generating ownership explanation prompt for parcel {parcel_id}")

            parcel = self.client.get_parcel_by_id(parcel_id)

            prompt = f"""Analyze the ownership structure of parcel {parcel.parcel_number}:

**Basic Information:**
- Parcel Number: {parcel.parcel_number}
- Municipality: {parcel.municipality_name}
- Total Area: {parcel.area} m²
- Address: {parcel.address or 'N/A'}

**Ownership Records:**
"""

            if parcel.possession_sheets:
                for idx, sheet in enumerate(parcel.possession_sheets, 1):
                    prompt += f"\nPossession Sheet {idx}:\n"
                    if sheet.possessors:
                        for possessor in sheet.possessors:
                            ownership = possessor.ownership or "Not specified"
                            prompt += f"  - {possessor.name}\n"
                            prompt += f"    Ownership: {ownership}\n"
                            if possessor.address:
                                prompt += f"    Address: {possessor.address}\n"
                    else:
                        prompt += "  No possessors listed\n"
            else:
                prompt += "\nNo ownership records available for this parcel.\n"

            prompt += """
Please explain:
1. Who owns this parcel and what are their ownership percentages?
2. Are there multiple owners (co-ownership)?
3. Are there any unusual aspects of the ownership structure?
4. What does this ownership structure typically indicate?
"""

            return prompt

        except CadastralAPIError as e:
            logger.error(f"Failed to generate ownership prompt for {parcel_id}: {e}", exc_info=True)
            raise ValueError(f"Could not retrieve parcel data for {parcel_id}.") from e

    async def property_report(self, parcel_id: str) -> str:
        """
        Generate a comprehensive property report prompt.

        Args:
            parcel_id: The unique parcel identifier

        Returns:
            Formatted prompt for generating a detailed property report
        """
        try:
            logger.info(f"Generating property report prompt for parcel {parcel_id}")

            parcel = self.client.get_parcel_by_id(parcel_id)

            prompt = f"""Generate a comprehensive property report for parcel {parcel.parcel_number}:

**Property Details:**
- Parcel Number: {parcel.parcel_number}
- Municipality: {parcel.municipality_name}
- Cadastral Office: {parcel.cadastral_office_name}
- Total Area: {parcel.area} m²
- Address: {parcel.address or 'N/A'}
- Building Rights: {'Yes' if parcel.has_building_right else 'No'}

**Land Use Classification:**
"""

            if parcel.parcel_parts:
                for part in parcel.parcel_parts:
                    prompt += f"  - {part.land_use_name}: {part.area} m²\n"
            else:
                prompt += "  No land use data available\n"

            prompt += "\n**Ownership:**\n"

            if parcel.possession_sheets:
                for sheet in parcel.possession_sheets:
                    if sheet.possessors:
                        for possessor in sheet.possessors:
                            ownership = possessor.ownership or "Not specified"
                            prompt += f"  - {possessor.name} ({ownership})\n"
            else:
                prompt += "  No ownership records available\n"

            prompt += """
Please create a detailed property report including:
1. Executive summary of the property
2. Land use breakdown and analysis
3. Ownership structure
4. Development potential (based on building rights)
5. Any notable features or restrictions
6. Market context (if relevant)
"""

            return prompt

        except CadastralAPIError as e:
            logger.error(f"Failed to generate property report for {parcel_id}: {e}", exc_info=True)
            raise ValueError(f"Could not retrieve parcel data for {parcel_id}.") from e

    async def compare_parcels(self, parcel_ids: list[str]) -> str:
        """
        Generate a prompt to compare multiple parcels.

        Args:
            parcel_ids: List of parcel identifiers to compare

        Returns:
            Formatted prompt with data for all parcels
        """
        try:
            logger.info(f"Generating comparison prompt for {len(parcel_ids)} parcels")

            if len(parcel_ids) < 2:
                raise ValueError("At least 2 parcels are required for comparison")

            prompt = "Compare the following parcels:\n\n"

            for idx, parcel_id in enumerate(parcel_ids, 1):
                try:
                    parcel = self.client.get_parcel_by_id(parcel_id)

                    prompt += f"**Parcel {idx}: {parcel.parcel_number}**\n"
                    prompt += f"- Municipality: {parcel.municipality_name}\n"
                    prompt += f"- Area: {parcel.area} m²\n"
                    prompt += f"- Building Rights: {'Yes' if parcel.has_building_right else 'No'}\n"

                    if parcel.parcel_parts:
                        prompt += "- Land Use: "
                        land_uses = [part.land_use_name for part in parcel.parcel_parts]
                        prompt += ", ".join(land_uses) + "\n"

                    if parcel.possession_sheets and parcel.possession_sheets[0].possessors:
                        owner_count = len(parcel.possession_sheets[0].possessors)
                        prompt += f"- Owners: {owner_count}\n"

                    prompt += "\n"

                except CadastralAPIError as e:
                    prompt += f"**Parcel {idx}: {parcel_id}** - Error: Could not retrieve data\n\n"
                    logger.error(f"Failed to fetch parcel {parcel_id}: {e}")

            prompt += """Please provide a comparative analysis including:
1. Size comparison and total area
2. Land use differences
3. Development potential comparison
4. Ownership structure differences
5. Which parcel might be more valuable/desirable and why?
6. Any other notable differences or similarities
"""

            return prompt

        except Exception as e:
            logger.error(f"Failed to generate comparison prompt: {e}", exc_info=True)
            raise ValueError(f"Could not generate comparison: {e}") from e

    async def land_use_summary(self, parcel_id: str) -> str:
        """
        Generate a prompt to analyze land use distribution.

        Args:
            parcel_id: The unique parcel identifier

        Returns:
            Formatted prompt for land use analysis
        """
        try:
            logger.info(f"Generating land use summary prompt for parcel {parcel_id}")

            parcel = self.client.get_parcel_by_id(parcel_id)

            prompt = f"""Analyze the land use distribution for parcel {parcel.parcel_number}:

**Parcel Information:**
- Parcel Number: {parcel.parcel_number}
- Municipality: {parcel.municipality_name}
- Total Area: {parcel.area} m²

**Land Use Breakdown:**
"""

            if parcel.parcel_parts:
                total_area = float(parcel.area) if parcel.area else 0

                for part in parcel.parcel_parts:
                    part_area = float(part.area) if part.area else 0
                    percentage = (part_area / total_area * 100) if total_area > 0 else 0

                    prompt += f"""
- **{part.land_use_name}**
  - Area: {part.area} m²
  - Percentage: {percentage:.1f}%
  - Code: {part.land_use}
"""
            else:
                prompt += "\nNo land use classification data available.\n"

            prompt += """
Please provide:
1. Summary of the land use distribution
2. What does this distribution tell us about the property?
3. Is this a single-use or mixed-use parcel?
4. What are the typical uses or development potential for each land category?
5. Any recommendations or observations about the land use pattern?
"""

            return prompt

        except CadastralAPIError as e:
            logger.error(f"Failed to generate land use summary for {parcel_id}: {e}", exc_info=True)
            raise ValueError(f"Could not retrieve parcel data for {parcel_id}.") from e
