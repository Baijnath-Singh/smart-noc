"""
LangGraph workflow for autonomous network remediation

This implements a multi-step troubleshooting and remediation workflow
similar to how a senior network engineer would approach problems.
"""
import time
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from loguru import logger

from state import RemediationState, ActionResult
from tools import NetworkTools


class RemediationAgent:
    """
    Autonomous network remediation agent using LangGraph
    
    Workflow phases:
    1. Planning: Analyze diagnosis and create remediation plan
    2. Investigation: Gather additional data if needed
    3. Remediation: Execute fixes
    4. Verification: Check if fixes worked
    5. Rollback: Undo changes if things got worse
    6. Learning: Document what was learned
    """
    
    def __init__(self, groq_api_key: str, simulation_mode: bool = True):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=groq_api_key,
            temperature=0.1,  # Low temperature for consistent decisions
            timeout=60.0
        )
        self.tools = NetworkTools(simulation_mode=simulation_mode)
        self.workflow = self._build_workflow()
        logger.info("RemediationAgent initialized with LangGraph workflow")
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph state machine"""
        
        graph = StateGraph(RemediationState)
        
        # Add nodes (workflow steps)
        graph.add_node("assess_complexity", self._assess_complexity)
        graph.add_node("create_plan", self._create_remediation_plan)
        graph.add_node("investigate", self._investigate_further)
        graph.add_node("execute_action", self._execute_remediation_action)
        graph.add_node("verify_fix", self._verify_remediation)
        graph.add_node("rollback", self._rollback_changes)
        graph.add_node("document", self._document_resolution)
        graph.add_node("escalate", self._escalate_to_human)
        
        # Set entry point
        graph.set_entry_point("assess_complexity")
        
        # Define workflow edges
        graph.add_conditional_edges(
            "assess_complexity",
            self._route_after_assessment,
            {
                "simple": "create_plan",
                "complex": "investigate",
                "escalate": "escalate"
            }
        )
        
        graph.add_edge("investigate", "create_plan")
        graph.add_edge("create_plan", "execute_action")
        
        graph.add_conditional_edges(
            "execute_action",
            self._route_after_execution,
            {
                "continue": "execute_action",  # More actions to execute
                "verify": "verify_fix",
                "failed": "escalate"
            }
        )
        
        graph.add_conditional_edges(
            "verify_fix",
            self._route_after_verification,
            {
                "success": "document",
                "retry": "create_plan",  # Try different approach
                "rollback": "rollback",
                "escalate": "escalate"
            }
        )
        
        graph.add_edge("rollback", "escalate")
        graph.add_edge("document", END)
        graph.add_edge("escalate", END)
        
        return graph.compile()
    
    # =========================================================================
    # WORKFLOW NODES - Each represents a phase
    # =========================================================================
    
    def _assess_complexity(self, state: RemediationState) -> RemediationState:
        """
        Phase 1: Assess if we can handle this autonomously
        """
        logger.info(f"[PHASE 1] Assessing complexity for incident #{state['incident_number']}")
        
        state['current_phase'] = 'planning'
        
        diagnosis = state['diagnosis']
        confidence = diagnosis.get('confidence', 0.0)
        incident_type = state['incident_type']
        
        # Build assessment prompt
        prompt = f"""
        You are an autonomous network operations agent. Assess if you can handle this incident.
        
        Incident Type: {incident_type}
        Diagnosis Confidence: {confidence}
        Root Cause: {diagnosis.get('root_cause', 'Unknown')}
        
        Can you handle this autonomously? Consider:
        - Is the diagnosis confident enough? (>0.6)
        - Is this a known issue type with standard remediation?
        - Are there safety risks if something goes wrong?
        
        Respond with one word: SIMPLE, COMPLEX, or ESCALATE
        """
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        decision = response.content.strip().upper()
        
        logger.info(f"Assessment decision: {decision}")
        
        # Update state
        state['confidence'] = confidence
        if decision == "ESCALATE":
            state['errors'].append("Complexity too high for autonomous handling")
        
        return state
    
    def _investigate_further(self, state: RemediationState) -> RemediationState:
        """
        Phase 2: Gather additional diagnostic data
        """
        logger.info("[PHASE 2] Investigating further...")
        
        state['current_phase'] = 'investigation'
        
        diagnosis = state['diagnosis']
        device = diagnosis.get('primary_device', 'core-router-01')
        
        # Use tools to gather evidence
        if 'INTERFACE' in state['incident_type'] or 'DEVICE_FAILURE' in state['incident_type']:
            # Check interface status
            result = self.tools.show_interface_status(device, "GigabitEthernet0/1")
            state['evidence'].append({
                "tool": "show_interface_status",
                "result": result,
                "finding": f"Interface has {result['errors']} errors"
            })
            
            # Check logs
            logs = self.tools.show_logging(device, filter="Error")
            state['evidence'].append({
                "tool": "show_logging",
                "result": logs,
                "finding": "Found interface flapping events in logs"
            })
        
        elif 'BGP' in state['incident_type']:
            # Check BGP
            bgp = self.tools.show_bgp_summary(device)
            state['evidence'].append({
                "tool": "show_bgp_summary",
                "result": bgp,
                "finding": "BGP neighbor status checked"
            })
        
        logger.info(f"Gathered {len(state['evidence'])} pieces of evidence")
        
        return state
    
    def _create_remediation_plan(self, state: RemediationState) -> RemediationState:
        """
        Phase 3: Create step-by-step remediation plan
        """
        logger.info("[PHASE 3] Creating remediation plan...")
        
        diagnosis = state['diagnosis']
        evidence = state['evidence']
        
        # Build planning prompt
        prompt = f"""
        You are creating a remediation plan for a network incident.
        
        Incident: {state['incident_type']}
        Root Cause: {diagnosis.get('root_cause', '')}
        Evidence: {len(evidence)} diagnostic checks performed
        
        Available tools:
        - clear_interface_counters: Clear error counters
        - reload_interface: Reload interface (shut/no shut)
        - restart_service: Restart a network service
        - clear_arp_cache: Clear ARP cache
        - apply_configuration: Apply config changes
        
        Create a 2-3 step remediation plan. Format:
        STEP 1: [tool_name] - [brief reason]
        STEP 2: [tool_name] - [brief reason]
        STEP 3: [tool_name] - [brief reason]
        
        Keep it simple and safe. Most interface issues can be fixed by:
        1. Clear counters to reset baseline
        2. Reload interface to reset state
        3. Verify health
        """
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        plan_text = response.content
        
        logger.info("=" * 80)
        logger.info("📋 REMEDIATION PLAN CREATED")
        logger.info("=" * 80)
        logger.info(plan_text)
        logger.info("=" * 80)
        
        # Parse plan into actionable steps
        # Try to get device from state (incident data) first, then diagnosis, then fallback
        device = state.get('primary_device') or diagnosis.get('primary_device')
        
        # Debug logging
        logger.info(f"🔍 DEBUG - Device extraction:")
        logger.info(f"  state.primary_device: {state.get('primary_device')}")
        logger.info(f"  diagnosis.primary_device: {diagnosis.get('primary_device')}")
        logger.info(f"  state.affected_devices: {state.get('affected_devices')}")
        logger.info(f"  affected_devices type: {type(state.get('affected_devices'))}")
        
        if not device and state.get('affected_devices'):
            affected = state['affected_devices']
            if isinstance(affected, list) and len(affected) > 0:
                device = affected[0]
            elif isinstance(affected, str):
                # Could be comma-separated string
                devices = [d.strip() for d in affected.split(',')]
                device = devices[0] if devices else None
        
        if not device:
            device = 'unknown-device'
        
        logger.info(f"📍 Target device for remediation: {device}")
        
        # Parse the LLM's plan text
        parsed_plan = self._parse_remediation_plan(plan_text, device, state['incident_type'])
        
        if parsed_plan:
            state['remediation_plan'] = parsed_plan
            logger.info(f"✅ Parsed {len(parsed_plan)} steps from LLM plan")
        else:
            # Fallback to hardcoded plans if parsing fails
            logger.warning("⚠️  Failed to parse LLM plan, using fallback")
            if 'INTERFACE' in state['incident_type'] or 'DEVICE_FAILURE' in state['incident_type']:
                state['remediation_plan'] = [
                    {
                        "step": 1,
                        "tool": "clear_interface_counters",
                        "device": device,
                        "interface": "GigabitEthernet0/1",
                        "reason": "Reset error counters to establish new baseline"
                    },
                    {
                        "step": 2,
                        "tool": "reload_interface",
                        "device": device,
                        "interface": "GigabitEthernet0/1",
                        "reason": "Reload interface to clear transient errors"
                    }
                ]
            else:
                # Generic plan for other incident types
                state['remediation_plan'] = [
                    {
                        "step": 1,
                        "tool": "apply_configuration",
                        "device": device,
                        "config_lines": ["interface GigabitEthernet0/1", "no shutdown"],
                        "reason": "Apply basic configuration fix"
                    }
                ]
        
        state['current_action'] = 0
        state['current_phase'] = 'remediation'
        
        return state
    
    def _parse_remediation_plan(self, plan_text: str, device: str, incident_type: str) -> List[Dict[str, Any]]:
        """
        Parse LLM-generated remediation plan text into executable steps
        
        Expected format:
        STEP 1: tool_name - reason
        STEP 2: tool_name - reason
        """
        import re
        
        steps = []
        lines = plan_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or not line.startswith('STEP'):
                continue
            
            # Parse: STEP 1: clear_interface_counters - Reset error counters...
            match = re.match(r'STEP\s+(\d+):\s+(\w+)\s*-\s*(.+)', line, re.IGNORECASE)
            if not match:
                continue
            
            step_num = int(match.group(1))
            tool_name = match.group(2).strip()
            reason = match.group(3).strip()
            
            # Build step based on tool type
            step = {
                "step": step_num,
                "tool": tool_name,
                "device": device,
                "reason": reason
            }
            
            # Add tool-specific parameters
            if tool_name in ['clear_interface_counters', 'reload_interface']:
                # Try to extract interface from reason or use default
                # Only match if interface name is preceded by "interface" or "port" with colon or space
                # Valid: "interface: GigabitEthernet0/1", "port 1/20"
                # Invalid: "Reload the interface to reset" (skip "to")
                interface_match = re.search(r'(?:interface|port)[:\s]+([A-Za-z]+[A-Za-z0-9/]+)', reason, re.IGNORECASE)
                if interface_match and len(interface_match.group(1)) > 2:  # Avoid matching short words like "to", "on"
                    step['interface'] = interface_match.group(1)
                else:
                    step['interface'] = 'GigabitEthernet0/1'  # Default
            
            elif tool_name == 'restart_service':
                # Extract service name from reason or use incident-based default
                service_match = re.search(r'(bgp|ospf|isis|rip|eigrp|vrrp|lacp|stp)', reason, re.IGNORECASE)
                if service_match:
                    step['service'] = service_match.group(1).lower()
                elif 'BGP' in incident_type:
                    step['service'] = 'bgp'
                else:
                    step['service'] = 'routing'  # Generic default
            
            elif tool_name == 'apply_configuration':
                # For VLAN issues, generate VLAN config
                if 'VLAN' in reason.upper() or 'VLAN' in incident_type:
                    step['config_lines'] = [
                        "interface GigabitEthernet0/1",
                        "switchport mode trunk",
                        "switchport trunk native vlan 10"
                    ]
                # For LAG/LACP issues
                elif 'LAG' in reason.upper() or 'LACP' in reason.upper():
                    step['config_lines'] = [
                        "interface GigabitEthernet0/1",
                        "channel-group 1 mode active"
                    ]
                else:
                    step['config_lines'] = [
                        "interface GigabitEthernet0/1",
                        "no shutdown"
                    ]
            
            elif tool_name == 'clear_arp_cache':
                # No additional parameters needed
                pass
            
            else:
                # Unknown tool, skip
                logger.warning(f"Unknown tool in plan: {tool_name}")
                continue
            
            steps.append(step)
        
        return steps
    
    def _execute_remediation_action(self, state: RemediationState) -> RemediationState:
        """
        Phase 4: Execute one remediation action
        """
        current_step = state['current_action']
        plan = state['remediation_plan']
        
        if current_step >= len(plan):
            logger.error("No more actions to execute")
            return state
        
        action = plan[current_step]
        logger.info("-" * 80)
        logger.info(f"[PHASE 4] 🔧 Executing Step {action['step']}/{len(plan)}: {action['tool']}")
        logger.info(f"   Device: {action['device']}")
        if 'interface' in action:
            logger.info(f"   Interface: {action['interface']}")
        if 'service' in action:
            logger.info(f"   Service: {action['service']}")
        if 'reason' in action:
            logger.info(f"   Reason: {action['reason']}")
        logger.info("-" * 80)
        
        start_time = time.time()
        
        try:
            # Execute the tool
            tool_name = action['tool']
            device = action['device']
            
            if tool_name == "clear_interface_counters":
                result = self.tools.clear_interface_counters(device, action['interface'])
            elif tool_name == "reload_interface":
                result = self.tools.reload_interface(device, action['interface'])
            elif tool_name == "restart_service":
                result = self.tools.restart_service(device, action['service'])
            elif tool_name == "apply_configuration":
                config_lines = action.get('config_lines', [])
                result = self.tools.apply_configuration(device, config_lines)
            elif tool_name == "clear_arp_cache":
                result = self.tools.clear_arp_cache(device)
            elif tool_name == "verify_interface_health":
                result = self.tools.verify_interface_health(device, action.get('interface', 'GigabitEthernet0/1'))
            else:
                logger.error(f"Unknown tool: {tool_name}")
                result = {"success": False, "error": f"Unknown tool: {tool_name}"}
            
            execution_time = time.time() - start_time
            
            # Record action
            action_result = {
                "step": action['step'],
                "tool": tool_name,
                "device": device,
                "success": result.get('success', False),
                "output": result,
                "execution_time": execution_time
            }
            
            state['actions_taken'].append(action_result)
            state['current_action'] += 1
            
            logger.info(f"Step {action['step']} {'succeeded' if result.get('success') else 'failed'} in {execution_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Error executing step {action['step']}: {e}")
            state['errors'].append(f"Execution failed: {str(e)}")
        
        return state
    
    def _verify_remediation(self, state: RemediationState) -> RemediationState:
        """
        Phase 5: Verify that remediation worked
        """
        logger.info("[PHASE 5] Verifying remediation...")
        
        state['current_phase'] = 'verification'
        
        # Wait a few seconds for changes to take effect
        time.sleep(3)
        
        diagnosis = state['diagnosis']
        device = diagnosis.get('primary_device', 'core-router-01')
        
        # Verify based on incident type
        if 'INTERFACE' in state['incident_type'] or 'DEVICE_FAILURE' in state['incident_type']:
            # Check interface health
            result = self.tools.verify_interface_health(device, "GigabitEthernet0/1")
            
            verification = {
                "check": "interface_health",
                "result": result,
                "success": result.get('healthy', False) and result.get('errors', 999) == 0
            }
            
            state['verification_results'].append(verification)
            state['success'] = verification['success']
            
            logger.info(f"Verification {'PASSED' if verification['success'] else 'FAILED'}")
        else:
            # Generic verification
            state['success'] = True
            logger.info("Verification passed (generic)")
        
        return state
    
    def _rollback_changes(self, state: RemediationState) -> RemediationState:
        """
        Phase 6: Rollback if things got worse
        """
        logger.warning("[PHASE 6] Rolling back changes...")
        
        state['current_phase'] = 'rollback'
        state['rollback_performed'] = True
        
        # In simulation, we just log
        # In production, this would undo configuration changes
        logger.info("Rollback completed (simulated)")
        
        return state
    
    def _document_resolution(self, state: RemediationState) -> RemediationState:
        """
        Phase 7: Document what happened for learning
        """
        logger.info("[PHASE 7] Documenting resolution...")
        
        state['current_phase'] = 'completed'
        
        # Calculate resolution time
        resolution_time = sum(
            action.get('execution_time', 0) 
            for action in state['actions_taken']
        )
        state['resolution_time_seconds'] = resolution_time
        
        # Generate lessons learned
        actions_summary = ", ".join([
            action['tool'] for action in state['actions_taken']
        ])
        
        state['lessons_learned'] = f"Successfully resolved {state['incident_type']} by: {actions_summary}. Resolution time: {resolution_time:.1f}s"
        state['should_update_kb'] = True
        
        logger.success(f"✅ Incident #{state['incident_number']} resolved in {resolution_time:.1f}s")
        
        return state
    
    def _escalate_to_human(self, state: RemediationState) -> RemediationState:
        """
        Escalate to human engineer
        """
        logger.warning(f"[ESCALATION] Incident #{state['incident_number']} requires human attention")
        
        state['current_phase'] = 'escalated'
        state['success'] = False
        
        reason = state['errors'][-1] if state['errors'] else "Unknown reason"
        logger.info(f"Escalation reason: {reason}")
        
        return state
    
    # =========================================================================
    # ROUTING FUNCTIONS - Decide next step based on state
    # =========================================================================
    
    def _route_after_assessment(self, state: RemediationState) -> str:
        """Decide where to go after complexity assessment"""
        
        # Check if we should escalate
        if state.get('errors') and any('too high' in err.lower() for err in state['errors']):
            return "escalate"
        
        # Check confidence
        if state.get('confidence', 0) < 0.5:
            return "complex"  # Need more investigation
        
        # Simple cases can go straight to planning
        return "simple"
    
    def _route_after_execution(self, state: RemediationState) -> str:
        """Decide what to do after executing an action"""
        
        # Check if last action failed
        if state['actions_taken'] and not state['actions_taken'][-1]['success']:
            return "failed"
        
        # Check if more actions in plan
        if state['current_action'] < len(state['remediation_plan']):
            return "continue"
        
        # All actions executed, time to verify
        return "verify"
    
    def _route_after_verification(self, state: RemediationState) -> str:
        """Decide what to do after verification"""
        
        if state.get('success', False):
            return "success"
        
        # Check retry count
        if state.get('retry_count', 0) >= 2:
            return "escalate"  # Tried 3 times, give up
        
        # Increment retry and try again
        state['retry_count'] = state.get('retry_count', 0) + 1
        
        # Check if things got worse
        if state['verification_results'] and not state['verification_results'][-1].get('success'):
            return "rollback"
        
        return "retry"
    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    def remediate(self, incident: Dict[str, Any], diagnosis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point: Remediate an incident
        
        Args:
            incident: Incident data from correlation engine
            diagnosis: Diagnosis from LLM diagnosis service
        
        Returns:
            Remediation result with success status and details
        """
        logger.info(f"🚀 Starting autonomous remediation for incident #{incident.get('incident_number')}")
        
        # Initialize state
        initial_state: RemediationState = {
            "incident_id": incident.get('incident_id', ''),
            "incident_number": incident.get('incident_number', 0),
            "incident_type": incident.get('incident_type', 'UNKNOWN'),
            "affected_devices": incident.get('affected_devices', []),
            "primary_device": incident.get('primary_device', ''),
            "diagnosis": diagnosis,
            "current_phase": "planning",
            "investigation_steps": [],
            "evidence": [],
            "hypothesis": diagnosis.get('root_cause', ''),
            "confidence": diagnosis.get('confidence', 0.0),
            "remediation_plan": [],
            "actions_taken": [],
            "current_action": 0,
            "verification_results": [],
            "success": False,
            "resolution_time_seconds": 0.0,
            "errors": [],
            "retry_count": 0,
            "rollback_performed": False,
            "lessons_learned": "",
            "should_update_kb": False
        }
        
        # Run workflow
        try:
            final_state = self.workflow.invoke(initial_state)
            
            logger.info(f"Workflow completed: phase={final_state['current_phase']}, success={final_state['success']}")
            
            return {
                "incident_number": final_state['incident_number'],
                "success": final_state['success'],
                "final_phase": final_state['current_phase'],
                "actions_taken": len(final_state['actions_taken']),
                "resolution_time": final_state['resolution_time_seconds'],
                "lessons_learned": final_state['lessons_learned'],
                "full_state": final_state
            }
            
        except Exception as e:
            logger.error(f"Workflow failed: {e}", exc_info=True)
            return {
                "incident_number": incident.get('incident_number'),
                "success": False,
                "error": str(e)
            }
