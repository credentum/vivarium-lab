# GovSim Experiment — backup manifest
Backed up: Tue Jul  7 01:14:48 AM UTC 2026 UTC
Source: claude-agent container, /claude-workspace/GovSim

## Git base
origin	https://github.com/giorgiopiatti/GovSim.git (fetch)
origin	https://github.com/giorgiopiatti/GovSim.git (push)
base commit: 1d11adf047b24fa2ba0d44a1d4931015ea2e5210 2025-01-19 17:33:56 +0100 Merge pull request #5 from pedrocurvo/fix/setup
branch: main

## Working-tree status at backup time
 M pathfinder
 M simulation/scenarios/common/environment/concurrent_env.py
?? EXPERIMENT_REPORT.md
?? analyze_validation_results.py
?? compare_results.py
?? extract_results.py
?? governance_library/
?? simulation/results/
?? simulation/scenarios/sheep/conf/experiment/exp_condition1_baseline.yaml
?? simulation/scenarios/sheep/conf/experiment/exp_condition2_soft_advisory.yaml
?? simulation/scenarios/sheep/conf/experiment/exp_condition3_hard_enforcement.yaml
?? simulation/scenarios/sheep/conf/experiment/exp_condition4_universalization_only.yaml
?? simulation/scenarios/sheep/conf/experiment/exp_condition5_soft_plus_universalization.yaml
?? simulation/scenarios/sheep/conf/experiment/exp_condition6_raw_math.yaml
?? simulation/scenarios/sheep/conf/experiment/sheep_governance_test.yaml
?? tests/

## Diff of tracked modifications (the code change behind the experiment)
diff --git a/simulation/scenarios/common/environment/concurrent_env.py b/simulation/scenarios/common/environment/concurrent_env.py
index c6a76da..4d609c6 100644
--- a/simulation/scenarios/common/environment/concurrent_env.py
+++ b/simulation/scenarios/common/environment/concurrent_env.py
@@ -14,6 +14,8 @@ from simulation.persona.common import (
     PersonaIdentity,
 )
 
+from governance_library import GovernanceMode, create_sustainable_pasture_policy_schema
+
 from .common import HarvestingObs
 
 
@@ -83,6 +85,22 @@ class ConcurrentEnv:
                     always_include=True,
                 )
             )
+        # Governance advisory — informational, no enforcement
+        if hasattr(self, 'governance_policy') and self.governance_policy:
+            if self.governance_policy.mode_enum == GovernanceMode.RAW_MATH:
+                advisory_text = self._generate_raw_math_advisory()
+            else:
+                advisory_text = self._generate_governance_advisory()
+            events.append(
+                PersonaEvent(
+                    advisory_text,
+                    created=self.internal_global_state["next_time"][agent],
+                    expiration=get_expiration_next_month(
+                        self.internal_global_state["next_time"][agent]
+                    ),
+                    always_include=True,
+                )
+            )
         obs = HarvestingObs(
             phase=self.phase,
             current_location=self.internal_global_state["next_location"][agent],
@@ -161,6 +179,82 @@ class ConcurrentEnv:
         )
         return state
 
+    def _generate_governance_advisory(self) -> str:
+        """Generate the locked advisory template for SOFT/HARD governance modes."""
+        pool_size = self.internal_global_state["resource_in_pool"]
+        num_agents = len(self.agents)
+        denominator = 2 * num_agents
+        sustainable_limit = pool_size // denominator
+        total_sustainable = sustainable_limit * num_agents
+
+        # Build harvest history table
+        if self.harvest_history:
+            lines = []
+            for round_idx, round_data in enumerate(self.harvest_history):
+                agent_harvests = ", ".join(
+                    f"{self.agent_id_to_name.get(a, a)}: {round_data.get(a, 0)}"
+                    for a in self.agents
+                )
+                lines.append(f"  Round {round_idx + 1}: {agent_harvests}")
+            harvest_history_table = "\n".join(lines)
+        else:
+            harvest_history_table = "  No previous rounds."
+
+        return (
+            f"=== Governance Advisory ===\n"
+            f"Current resource pool: {pool_size} hectares.\n"
+            f"Number of agents: {num_agents}.\n"
+            f"Sustainable harvest limit per agent: {sustainable_limit} hectares "
+            f"(calculated as pool / {denominator}).\n"
+            f"\n"
+            f"If the total harvest by all agents stays at or below {total_sustainable} "
+            f"hectares, the resource will regenerate to its current level or higher next "
+            f"round. If total harvest exceeds {total_sustainable} hectares, the resource "
+            f"will decline.\n"
+            f"\n"
+            f"Harvest history from previous rounds:\n"
+            f"{harvest_history_table}\n"
+            f"\n"
+            f"You may harvest any amount you choose. This advisory is informational only.\n"
+            f"=== End Advisory ==="
+        )
+
+    def _generate_raw_math_advisory(self) -> str:
+        """Generate raw information template — inputs only, no calculated answer."""
+        pool_size = self.internal_global_state["resource_in_pool"]
+        num_agents = len(self.agents)
+        max_pool = self.cfg.initial_resource_in_pool
+        collapse_threshold = 5
+
+        # Build harvest history table (same format as governance advisory)
+        if self.harvest_history:
+            lines = []
+            for round_idx, round_data in enumerate(self.harvest_history):
+                agent_harvests = ", ".join(
+                    f"{self.agent_id_to_name.get(a, a)}: {round_data.get(a, 0)}"
+                    for a in self.agents
+                )
+                lines.append(f"  Round {round_idx + 1}: {agent_harvests}")
+            harvest_history_table = "\n".join(lines)
+        else:
+            harvest_history_table = "  No previous rounds."
+
+        return (
+            f"=== Resource Information ===\n"
+            f"Current resource pool: {pool_size} hectares.\n"
+            f"Number of agents sharing this resource: {num_agents}.\n"
+            f"Regeneration rule: After all harvests, the remaining grass "
+            f"doubles (maximum {max_pool}).\n"
+            f"Collapse threshold: If the pool drops below {collapse_threshold} "
+            f"hectares, the resource is permanently destroyed.\n"
+            f"\n"
+            f"Harvest history from previous rounds:\n"
+            f"{harvest_history_table}\n"
+            f"\n"
+            f"You may harvest any amount you choose.\n"
+            f"=== End Resource Information ==="
+        )
+
     def _observe(self, agent) -> HarvestingObs:
         """
         Observe should return the observation of the specified agent.
@@ -203,6 +297,7 @@ class ConcurrentEnv:
 
         self.num_round = 0
         self.df_acc = []
+        self.harvest_history = []  # list of dicts: [{agent: amount, ...}, ...]
 
         # RL specific (for pettingzoo)
         self.rewards = {}
@@ -226,6 +321,64 @@ class ConcurrentEnv:
         for agent in self.agents:
             self._init_agent(agent)
 
+        # Initialize governance policy from experiment configuration
+        """
+        CRITICAL_LLM_CONTEXT:
+            - Governance modes control commons resource management:
+              * NONE: Baseline (agents self-regulate, typically collapse)
+              * SOFT: Advisory limits provided in agent observations
+              * HARD: Enforced caps on harvest requests (see lines 375-387)
+
+            - Configuration format supports two patterns:
+              * Nested: cfg.governance = {enabled: true, mode: 'hard'}
+              * Flat: cfg.governance_mode = GovernanceMode.HARD
+
+            - Policy factory: create_sustainable_pasture_policy_schema()
+            - Sustainable formula: max_per_agent = resource_pool ÷ (2 × num_agents)
+            - Ensures ≤50% total harvest, leaving ≥50% to double back to 100
+
+        WHY: GovSim NeurIPS 2024 showed 43/45 runs collapse without governance.
+             Only GPT-4 and Claude-3-Opus succeeded. This library enables
+             weaker models to survive by encoding expert sustainability rules.
+
+        EVIDENCE: Enforcement at lines 375-387 caps violations automatically.
+                  Factory: governance_library/commons_governance_schema.py:308
+        """
+        governance_mode_enum = GovernanceMode.NONE
+
+        if hasattr(self.cfg, 'governance') and self.cfg.governance.get('enabled', False):
+            mode_string = self.cfg.governance.get('mode', 'none').lower()
+            try:
+                governance_mode_enum = GovernanceMode(mode_string)
+            except ValueError:
+                import logging
+                valid_modes_list = [m.value for m in GovernanceMode]
+                logging.warning(
+                    f"Invalid governance mode '{mode_string}' in config. "
+                    f"Valid options: {valid_modes_list}. Defaulting to NONE."
+                )
+                governance_mode_enum = GovernanceMode.NONE
+        elif hasattr(self.cfg, 'governance_mode'):
+            if isinstance(self.cfg.governance_mode, GovernanceMode):
+                governance_mode_enum = self.cfg.governance_mode
+            else:
+                try:
+                    governance_mode_enum = GovernanceMode[self.cfg.governance_mode.upper()]
+                except (KeyError, AttributeError):
+                    import logging
+                    logging.warning(
+                        f"Invalid governance_mode '{self.cfg.governance_mode}' in config. "
+                        f"Defaulting to NONE."
+                    )
+                    governance_mode_enum = GovernanceMode.NONE
+
+        if governance_mode_enum != GovernanceMode.NONE:
+            self.governance_policy = create_sustainable_pasture_policy_schema(
+                mode_enum=governance_mode_enum
+            )
+        else:
+            self.governance_policy = None
+
         self._agent_selector = agent_selector(self.agents)
         self.agent_selection = self._agent_selector.next()
         self._phase_selector = agent_selector(
@@ -342,6 +495,9 @@ class ConcurrentEnv:
             action = self.internal_global_state["action"][agent]
             self.log_step_harvest(action, res)
 
+        # Record harvest history for governance advisory
+        self.harvest_history.append(dict(resource_per_agent))
+
         for agent in self.agents:
             res = resource_per_agent[agent]
             self.internal_global_state["collected_resource"][agent] += res
@@ -350,8 +506,25 @@ class ConcurrentEnv:
             self.rewards[agent] += res
 
     def _step_lake_bet(self, action: PersonaActionHarvesting):
-        res = action.quantity
-        self.internal_global_state["wanted_resource"][self.agent_selection] = res
+        requested_harvest_int = action.quantity
+
+        # Validate against governance policy (HARD mode only — SOFT mode is advisory)
+        if (hasattr(self, 'governance_policy') and self.governance_policy
+                and self.governance_policy.mode_enum == GovernanceMode.HARD):
+            resource_pool_int = self.internal_global_state["resource_in_pool"]
+            num_agents_int = len(self.agents)
+
+            is_within_limit_bool = self.governance_policy.validate_harvest_decision_boolean(
+                requested_harvest_int, resource_pool_int, num_agents_int
+            )
+
+            if not is_within_limit_bool:
+                # Cap at max allowed to maintain sustainability
+                requested_harvest_int = self.governance_policy.calculate_max_allowed_harvest_int(
+                    resource_pool_int, num_agents_int
+                )
+
+        self.internal_global_state["wanted_resource"][self.agent_selection] = requested_harvest_int
         self.internal_global_state["action"][self.agent_selection] = action
         self.internal_global_state["next_location"][
             self.agent_selection
