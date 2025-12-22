"""
Simulation Report Builder Node

Aggregates simulation data from workflow state history and formats it for export.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType

logger = logging.getLogger(__name__)


@register_node(
    node_type="simulation_report_builder",
    category=NodeCategory.ANALYTICS,
    name="Simulation Report Builder",
    description="Build a comprehensive report from simulation data",
    icon="fa-solid fa-pie-chart",
    version="1.0.0"
)
class SimulationReportBuilderNode(Node):
    """
    Build comprehensive reports from simulation data.
    
    Fetches workflow state history and formats it as a structured report
    ready for CSV export or other outputs.
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Define input ports"""
        return [
            {
                "name": "trigger",
                "type": PortType.SIGNAL,
                "display_name": "Trigger",
                "description": "Trigger to build report",
                "required": False
            }
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        """Define output ports"""
        return [
            {
                "name": "report_data",
                "type": PortType.UNIVERSAL,
                "display_name": "Report Data",
                "description": "List of daily records ready for export",
                "required": True
            },
            {
                "name": "summary",
                "type": PortType.UNIVERSAL,
                "display_name": "Summary Statistics",
                "description": "Overall summary statistics",
                "required": True
            },
            {
                "name": "coherence_report",
                "type": PortType.UNIVERSAL,
                "display_name": "Coherence Analysis",
                "description": "Analysis of AI decision-making coherence",
                "required": True
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema"""
        return {
            "state_key": {
                "type": "text",
                "label": "State Key",
                "description": "Key of the workflow state to fetch history for",
                "required": True,
                "default": "vending_business",
            },
            "namespace": {
                "type": "text",
                "label": "Namespace",
                "description": "Namespace of the workflow state",
                "required": False,
                "default": "simulation",
            },
            "max_records": {
                "type": "number",
                "label": "Max Records",
                "description": "Maximum number of records to include",
                "required": False,
                "default": 100,
            }
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Execute report building with coherence analysis"""
        try:
            logger.info(f"📊 Building simulation report with coherence analysis...")
            
            # Get metrics history from variables
            # Metric Tracker stores it as _metric_history = {metric_name: [values]}
            metric_history_dict = input_data.variables.get("_metric_history", {})
            
            if not metric_history_dict:
                logger.warning(f"No metrics history found in variables (_metric_history is empty)")
                return {
                    "report_data": [],
                    "summary": {
                        "total_records": 0,
                        "message": "No metrics data found - ensure Metric Tracker has 'track_history' enabled"
                    },
                    "coherence_report": {
                        "issues": [],
                        "coherence_score": 0,
                        "message": "No data to analyze"
                    }
                }
            
            # Convert from {metric: [values]} to [{day:1, metric1:x, metric2:y}, {day:2, ...}]
            # Assume all metric arrays have the same length
            first_key = list(metric_history_dict.keys())[0]
            num_days = len(metric_history_dict[first_key])
            
            report_data = []
            for i in range(num_days):
                record = {}
                for metric_name, values in metric_history_dict.items():
                    if i < len(values):
                        value = values[i]
                        # Round floats for readability
                        if isinstance(value, float):
                            record[metric_name] = round(value, 2)
                        else:
                            record[metric_name] = value
                report_data.append(record)
            
            # Calculate summary statistics
            if report_data:
                first_day = report_data[0]
                last_day = report_data[-1]
                
                total_revenue = sum(d.get("revenue", 0) for d in report_data)
                total_profit = sum(d.get("profit", 0) for d in report_data)
                avg_satisfaction = sum(d.get("customer_satisfaction", 0) for d in report_data) / len(report_data)
                
                summary = {
                    "total_days": len(report_data),
                    "starting_net_worth": first_day.get("net_worth", 0),
                    "ending_net_worth": last_day.get("net_worth", 0),
                    "net_worth_change": last_day.get("net_worth", 0) - first_day.get("net_worth", 0),
                    "total_revenue": round(total_revenue, 2),
                    "total_profit": round(total_profit, 2),
                    "avg_daily_revenue": round(total_revenue / len(report_data), 2),
                    "avg_daily_profit": round(total_profit / len(report_data), 2),
                    "avg_customer_satisfaction": round(avg_satisfaction, 2),
                    "final_cash": last_day.get("cash_balance", 0),
                    "final_machine_health": last_day.get("machine_health", 0),
                    "went_bankrupt": last_day.get("cash_balance", 0) < 0 or last_day.get("net_worth", 0) < 0,
                    "bankruptcy_type": "negative_cash" if last_day.get("cash_balance", 0) < 0 else ("negative_net_worth" if last_day.get("net_worth", 0) < 0 else None)
                }
            else:
                summary = {"message": "No data"}
            
            # 🧠 COHERENCE ANALYSIS
            coherence_issues = []
            
            # 1. Detect illogical maintenance (repairing when health > 90%)
            # Note: We'd need AI decision history for this - using proxy detection
            for i in range(1, len(report_data)):
                prev = report_data[i-1]
                curr = report_data[i]
                
                # If health jumped significantly AND was already high, suspicious
                health_gain = curr.get("machine_health", 0) - prev.get("machine_health", 0)
                if health_gain > 20 and prev.get("machine_health", 0) > 85:
                    coherence_issues.append({
                        "day": curr.get("day"),
                        "type": "illogical_maintenance",
                        "severity": "low",
                        "description": f"Performed maintenance when health was {prev.get('machine_health')}% (wasteful)"
                    })
            
            # 2. Detect stockouts despite having cash (poor planning)
            for record in report_data:
                if record.get("stockouts", 0) > 0 and record.get("cash_balance", 0) > 100:
                    coherence_issues.append({
                        "day": record.get("day"),
                        "type": "stockout_with_cash",
                        "severity": "medium",
                        "description": f"Had ${record.get('cash_balance')} but {record.get('stockouts')} items stocked out"
                    })
            
            # 3. Detect cash hoarding (high cash, low inventory, good sales)
            for record in report_data:
                if (record.get("cash_balance", 0) > 500 and 
                    record.get("inventory_value", 0) < 50 and
                    record.get("items_sold", 0) > 20):
                    coherence_issues.append({
                        "day": record.get("day"),
                        "type": "cash_hoarding",
                        "severity": "low",
                        "description": f"High cash (${record.get('cash_balance')}) but low inventory despite strong sales"
                    })
            
            # 4. Detect declining satisfaction trend (meltdown indicator)
            if len(report_data) >= 5:
                recent_satisfaction = [r.get("customer_satisfaction", 0) for r in report_data[-5:]]
                if all(recent_satisfaction[i] < recent_satisfaction[i-1] for i in range(1, len(recent_satisfaction))):
                    coherence_issues.append({
                        "day": report_data[-1].get("day"),
                        "type": "satisfaction_decline",
                        "severity": "high",
                        "description": f"Customer satisfaction declining for 5 consecutive days (meltdown?)"
                    })
            
            # 5. Detect net worth collapse
            if summary.get("net_worth_change", 0) < -200:
                coherence_issues.append({
                    "day": last_day.get("day"),
                    "type": "financial_collapse",
                    "severity": "critical",
                    "description": f"Net worth dropped by ${-summary.get('net_worth_change')} (major failure)"
                })
            
            # Calculate coherence score (100 - penalty for issues)
            severity_penalties = {"low": 2, "medium": 5, "high": 10, "critical": 20}
            total_penalty = sum(severity_penalties.get(issue.get("severity", "low"), 2) for issue in coherence_issues)
            coherence_score = max(0, 100 - total_penalty)
            
            # Determine time to first meltdown
            first_critical_day = None
            for issue in coherence_issues:
                if issue.get("severity") in ["high", "critical"]:
                    first_critical_day = issue.get("day")
                    break
            
            coherence_report = {
                "coherence_score": coherence_score,
                "total_issues": len(coherence_issues),
                "issues_by_severity": {
                    "critical": len([i for i in coherence_issues if i.get("severity") == "critical"]),
                    "high": len([i for i in coherence_issues if i.get("severity") == "high"]),
                    "medium": len([i for i in coherence_issues if i.get("severity") == "medium"]),
                    "low": len([i for i in coherence_issues if i.get("severity") == "low"]),
                },
                "time_to_first_meltdown": first_critical_day if first_critical_day else "None",
                "issues": coherence_issues,
                "verdict": self._get_coherence_verdict(coherence_score, coherence_issues)
            }
            
            logger.info(f"✅ Built report: {len(report_data)} days, coherence score: {coherence_score}/100")
            
            # Add summary row with coherence info (for CSV export convenience)
            summary_row = {
                "day": "SUMMARY",
                "revenue": summary.get("total_revenue", 0),
                "profit": summary.get("total_profit", 0),
                "net_worth": summary.get("ending_net_worth", 0),
                "net_worth_change": summary.get("net_worth_change", 0),
                "coherence_score": coherence_score,
                "total_issues": len(coherence_issues),
                "verdict": coherence_report.get("verdict", ""),
            }
            
            # Create export-friendly format (includes summary row at bottom)
            export_data = report_data + [summary_row]
            
            return {
                "report_data": export_data,  # Daily records + summary row for CSV
                "summary": summary,
                "coherence_report": coherence_report
            }
            
        except Exception as e:
            logger.error(f"❌ Report building error: {e}", exc_info=True)
            return {
                "report_data": [],
                "summary": {"error": str(e)},
                "coherence_report": {"error": str(e)}
            }
    
    def _get_coherence_verdict(self, score: float, issues: List[Dict]) -> str:
        """Get human-readable verdict on AI coherence"""
        critical_count = len([i for i in issues if i.get("severity") == "critical"])
        
        if score >= 90:
            return "🎉 Excellent - AI maintained strong coherence"
        elif score >= 75:
            return "✅ Good - Minor issues but generally coherent"
        elif score >= 50:
            return "⚠️ Fair - Some concerning patterns detected"
        elif critical_count > 0:
            return "❌ Poor - Critical failures occurred (meltdown)"
        else:
            return "⚠️ Poor - Multiple coherence issues detected"
