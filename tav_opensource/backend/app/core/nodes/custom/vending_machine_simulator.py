"""
Vending Machine Simulator Node

Simulates a day of vending machine operations.
This is a CUSTOM node example for the hackathon.
"""

from typing import Any, Dict, Optional, List
import logging
import random
import json

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import PortType, NodeCategory

logger = logging.getLogger(__name__)


@register_node(
    node_type="vending_machine_simulator",
    category=NodeCategory.BUSINESS,
    name="Vending Machine Simulator",
    description="Simulates daily vending machine operations",
    icon="fa-solid fa-building"
)
class VendingMachineSimulatorNode(Node):
    """
    Simulates a day of vending machine operations.
    
    Simulates:
    - Customer arrivals (random)
    - Purchase attempts
    - Inventory depletion
    - Revenue generation
    - Machine degradation
    - Customer satisfaction
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "trigger",
                "type": PortType.SIGNAL,
                "display_name": "Trigger",
                "description": "Trigger daily simulation",
                "required": False
            },
            {
                "name": "current_state",
                "type": PortType.UNIVERSAL,
                "display_name": "Current State",
                "description": "Current business state (inventory, cash, etc.)",
                "required": True
            },
            {
                "name": "ai_actions",
                "type": PortType.UNIVERSAL,
                "display_name": "AI Actions",
                "description": "Actions from AI agent (restock, maintenance, etc.)",
                "required": False
            },
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "new_state",
                "type": PortType.UNIVERSAL,
                "display_name": "New State",
                "description": "Updated business state after simulation"
            },
            {
                "name": "metrics",
                "type": PortType.UNIVERSAL,
                "display_name": "Daily Metrics",
                "description": "KPIs for the day (revenue, items sold, etc.)"
            },
            {
                "name": "events",
                "type": PortType.UNIVERSAL,
                "display_name": "Events",
                "description": "Notable events during the day"
            },
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            # === Customer & Demand Settings ===
            "avg_customers_per_day": {
                "label": "Average Customers Per Day",
                "type": "number",
                "default": 50,
                "description": "Average number of customers per day",
            },
            
            # === Pricing Settings ===
            "use_ai_pricing": {
                "label": "Use AI Dynamic Pricing",
                "type": "boolean",
                "default": False,
                "description": "If true, AI Agent controls prices. If false, use fixed prices below.",
            },
            "item_prices": {
                "label": "Fixed Item Prices (if not using AI pricing)",
                "type": "json",
                "description": "Price per item (JSON object)",
                "default": {
                    "cola": 2.5,
                    "water": 1.5,
                    "chips": 1.0
                },
                "placeholder": '{"cola": 2.5, "water": 1.5, "chips": 1.0}'
            },
            
            # === Cost Settings ===
            "daily_rent": {
                "label": "Daily Rent ($)",
                "type": "number",
                "default": 50,
                "description": "Fixed daily rent cost for the vending machine location",
            },
            "daily_electricity": {
                "label": "Daily Electricity ($)",
                "type": "number",
                "default": 10,
                "description": "Daily electricity and utilities cost",
            },
            "maintenance_cost": {
                "label": "Maintenance Cost ($)",
                "type": "number",
                "default": 100,
                "description": "Cost when AI performs maintenance",
            },
            "item_cost_per_unit": {
                "label": "Item Cost Per Unit ($)",
                "type": "number",
                "default": 0.5,
                "description": "How much each item costs to restock (applies to all items)",
            },
            
            # === Machine Settings ===
            "machine_degradation_rate": {
                "label": "Machine Degradation Rate (%/day)",
                "type": "number",
                "default": 2,
                "description": "How much machine health degrades per day (in %)",
            },
            "maintenance_health_boost": {
                "label": "Maintenance Health Boost (%)",
                "type": "number",
                "default": 30,
                "description": "How much health is restored when maintenance is performed",
            },
            
            # === Order Delivery Settings ===
            "enable_delivery_delays": {
                "label": "Enable Order Delivery Delays",
                "type": "boolean",
                "default": False,
                "description": "If true, orders take 2-3 days to arrive (tests long-term planning)",
            },
            "delivery_delay_days": {
                "label": "Delivery Delay (days)",
                "type": "number",
                "default": 2,
                "description": "How many days it takes for orders to arrive",
            },
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Simulate a day of vending machine operations"""
        
        state = input_data.ports.get("current_state", {})
        ai_actions = input_data.ports.get("ai_actions", {})
        
        # Get config - Customer & Demand
        avg_customers_raw = self.resolve_config(input_data, "avg_customers_per_day", 50)
        try:
            avg_customers = int(avg_customers_raw)
        except (ValueError, TypeError):
            avg_customers = 50
        
        # Get config - Pricing
        use_ai_pricing = self.resolve_config(input_data, "use_ai_pricing", False)
        item_prices = self.resolve_config(input_data, "item_prices", {
            "cola": 2.5, "water": 1.5, "chips": 1.0
        })
        
        # Get config - Costs
        daily_rent = float(self.resolve_config(input_data, "daily_rent", 50))
        daily_electricity = float(self.resolve_config(input_data, "daily_electricity", 10))
        maintenance_cost = float(self.resolve_config(input_data, "maintenance_cost", 100))
        item_cost = float(self.resolve_config(input_data, "item_cost_per_unit", 0.5))
        
        # Get config - Machine
        degradation_raw = self.resolve_config(input_data, "machine_degradation_rate", 2)
        try:
            degradation = float(degradation_raw)
        except (ValueError, TypeError):
            degradation = 2.0
        
        maintenance_boost = float(self.resolve_config(input_data, "maintenance_health_boost", 30))
        
        # Get config - Delivery
        enable_delays = self.resolve_config(input_data, "enable_delivery_delays", False)
        delivery_delay = int(self.resolve_config(input_data, "delivery_delay_days", 2))
        
        # Parse item_prices if it's a string
        if isinstance(item_prices, str) and item_prices:
            try:
                item_prices = json.loads(item_prices)
            except (json.JSONDecodeError, ValueError):
                logger.warning(f"Could not parse item_prices as JSON: {item_prices}")
                item_prices = {"cola": 2.5, "water": 1.5, "chips": 1.0}
        
        # Initialize state if missing
        inventory = state.get("inventory", {
            "cola": 20, "water": 15, "chips": 30
        })
        cash = state.get("cash", 0)
        total_revenue = state.get("total_revenue", 0)
        machine_health = state.get("machine_health", 100)
        day = state.get("day", 1)
        pending_orders = state.get("pending_orders", [])
        
        # Parse ai_actions if it's a string
        if isinstance(ai_actions, str) and ai_actions:
            try:
                ai_actions = json.loads(ai_actions)
            except (json.JSONDecodeError, ValueError):
                logger.warning(f"Could not parse ai_actions as JSON: {ai_actions}")
                ai_actions = {}
        
        # Process pending orders (if delivery delays enabled)
        orders_arrived = []
        if enable_delays and pending_orders:
            new_pending = []
            for order in pending_orders:
                if order.get("arrival_day", 999) <= day:
                    # Order arrived!
                    for item, qty in order.get("items", {}).items():
                        if item in inventory:
                            inventory[item] += qty
                    orders_arrived.append(order)
                    logger.info(f"📦 Order arrived: {order.get('items')}")
                else:
                    new_pending.append(order)
            pending_orders = new_pending
        
        # If using AI pricing, extract prices from AI actions
        if use_ai_pricing and ai_actions:
            ai_prices = ai_actions.get("prices", {})
            if ai_prices:
                item_prices.update(ai_prices)
                logger.info(f"💰 AI set prices: {ai_prices}")
        
        # Apply AI actions (restock, maintenance)
        restock_cost = 0
        maintenance_performed = False
        
        if ai_actions:
            if ai_actions.get("restock"):
                restock_items = ai_actions.get("restock_items", {})
                
                # Calculate restock cost (same for both immediate and delayed delivery)
                for item, qty in restock_items.items():
                    restock_cost += qty * item_cost
                
                if enable_delays:
                    # Add to pending orders (pay now, receive later)
                    pending_orders.append({
                        "items": restock_items,
                        "arrival_day": day + delivery_delay,
                        "ordered_on": day
                    })
                    logger.info(f"📋 AI ordered: {restock_items} (arrives day {day + delivery_delay})")
                else:
                    # Immediate delivery (pay and receive now)
                    for item, qty in restock_items.items():
                        if item in inventory:
                            inventory[item] += qty
                    logger.info(f"🔄 AI restocked: {restock_items}")
                
                # Deduct payment
                cash -= restock_cost
            
            if ai_actions.get("maintenance"):
                machine_health = min(100, machine_health + maintenance_boost)
                cash -= maintenance_cost
                maintenance_performed = True
                logger.info(f"🔧 AI performed maintenance (cost: ${maintenance_cost})")
        
        # Simulate customer arrivals
        num_customers = max(0, int(random.gauss(avg_customers, avg_customers * 0.2)))
        
        daily_revenue = 0
        items_sold = {}
        stockouts = []
        failed_purchases = 0
        
        # Simulate each customer
        malfunction_failures = 0  # Track failures due to machine health
        for i in range(num_customers):
            # Random product selection
            items = list(inventory.keys())
            if not items:
                break
            
            selected_item = random.choice(items)
            
            # Check if in stock
            if inventory[selected_item] > 0:
                # Machine health affects success rate
                success_rate = machine_health / 100
                
                if random.random() < success_rate:
                    # Successful purchase
                    inventory[selected_item] -= 1
                    price = item_prices.get(selected_item, 2.0)
                    daily_revenue += price
                    
                    items_sold[selected_item] = items_sold.get(selected_item, 0) + 1
                else:
                    # Machine malfunction (item was available but machine failed)
                    failed_purchases += 1
                    malfunction_failures += 1
            else:
                # Stockout
                if selected_item not in stockouts:
                    stockouts.append(selected_item)
                failed_purchases += 1
        
        # Update cash and revenue
        cash += daily_revenue
        total_revenue += daily_revenue
        
        # Calculate costs (NEW: includes operating costs!)
        cost_of_goods_sold = sum(items_sold.values()) * item_cost
        cash -= cost_of_goods_sold  # Deduct cost of goods sold
        
        operating_costs = daily_rent + daily_electricity
        if maintenance_performed:
            operating_costs += maintenance_cost
        
        total_daily_costs = cost_of_goods_sold + operating_costs + restock_cost
        daily_profit = daily_revenue - total_daily_costs
        
        # Deduct operating costs from cash
        cash -= operating_costs
        
        # Machine degradation
        machine_health = max(0, machine_health - degradation)
        
        # Customer satisfaction (based on success rate)
        success_rate = (num_customers - failed_purchases) / max(num_customers, 1)
        customer_satisfaction = success_rate * 100
        
        # Calculate net worth (Cash + Inventory Value)
        inventory_value = sum(qty * item_cost for qty in inventory.values())
        net_worth = cash + inventory_value
        
        # Track AI decision history (last 5 decisions)
        recent_decisions = state.get("recent_decisions", [])
        
        # Record today's decision
        if ai_actions:
            decision_record = {
                "day": day,
                "restock": ai_actions.get("restock", False),
                "restock_items": ai_actions.get("restock_items", {}),
                "maintenance": ai_actions.get("maintenance", False),
                "reasoning": ai_actions.get("reasoning", "No reasoning provided"),
                "inventory_before": {k: v for k, v in state.get("inventory", {}).items()},  # Snapshot
                "cash_before": state.get("cash", 0)
            }
            recent_decisions.append(decision_record)
            
            # Keep only last 5 decisions
            if len(recent_decisions) > 5:
                recent_decisions = recent_decisions[-5:]
        
        # Create formatted decision history for AI readability
        decision_summary = []
        for dec in recent_decisions[-5:]:
            summary_line = f"Day {dec['day']}: "
            if dec.get('restock'):
                items_str = ', '.join([f"{k}:{v}" for k, v in dec.get('restock_items', {}).items()])
                summary_line += f"Restocked {items_str}"
            else:
                summary_line += "No restock"
            
            if dec.get('maintenance'):
                summary_line += ", Did maintenance"
            
            summary_line += f" | Reasoning: {dec.get('reasoning', 'N/A')[:80]}"
            decision_summary.append(summary_line)
        
        decision_history_text = "\n".join(decision_summary) if decision_summary else "No previous decisions"
        
        # === APPROACH 2: LESSONS LEARNED ===
        # Detect mistakes and generate explicit lessons for the AI
        lessons_learned = state.get("lessons_learned", [])
        
        # Calculate average daily sales from recent decisions for better planning
        avg_daily_sales = 50  # Default assumption
        if len(recent_decisions) >= 2:
            # Calculate items sold per day based on inventory changes
            total_items_across_days = 0
            days_counted = 0
            for i, dec in enumerate(recent_decisions[-3:]):
                inv_before = dec.get("inventory_before", {})
                # For the first decision, we don't have a previous inventory to compare
                if i > 0:
                    prev_inv = recent_decisions[-3:][i-1].get("inventory_before", {})
                    items_change = sum(inv_before.values()) - sum(prev_inv.values())
                    if items_change < 0:  # Items were sold (inventory decreased)
                        total_items_across_days += abs(items_change)
                        days_counted += 1
            
            if days_counted > 0:
                avg_daily_sales = max(30, total_items_across_days / days_counted)
        
        # Detect mistakes and generate lessons
        new_lessons = []
        
        # MISTAKE 1: Stockout with available cash (most critical!)
        total_inventory = sum(inventory.values())
        if len(stockouts) > 0 and cash > 100:
            lesson = {
                "day": day,
                "type": "stockout_with_cash",
                "severity": "high",
                "mistake": f"Stockout occurred ({len(stockouts)} items) despite having ${cash:.0f} available",
                "lesson": f"With {delivery_delay}-day delivery delays, order when inventory < {avg_daily_sales * (delivery_delay + 1):.0f} items (current avg sales: {avg_daily_sales:.0f}/day)",
                "rule": f"Order threshold = avg_daily_sales × (delivery_delay + buffer) = {avg_daily_sales:.0f} × {delivery_delay + 1} = {avg_daily_sales * (delivery_delay + 1):.0f} items"
            }
            new_lessons.append(lesson)
            logger.warning(f"⚠️ LESSON LEARNED (Day {day}): {lesson['mistake']}")
        
        # MISTAKE 2: Ordering too late (inventory won't last through delivery window)
        if enable_delays and total_inventory > 0 and total_inventory < avg_daily_sales * delivery_delay:
            # Check if AI ordered today
            ordered_today = ai_actions and ai_actions.get("restock", False)
            if not ordered_today and not pending_orders:
                lesson = {
                    "day": day,
                    "type": "late_ordering",
                    "severity": "high",
                    "mistake": f"Inventory ({total_inventory} items) won't last {delivery_delay} days at current sales rate ({avg_daily_sales:.0f}/day)",
                    "lesson": f"Order NOW! Current stock will run out before delivery arrives (need {avg_daily_sales * delivery_delay:.0f} items to survive delivery window)",
                    "rule": "Order when: current_inventory < (avg_daily_sales × delivery_delay)"
                }
                new_lessons.append(lesson)
                logger.warning(f"⚠️ LESSON LEARNED (Day {day}): {lesson['mistake']}")
        
        # MISTAKE 3: Excessive cash hoarding while business suffers
        if cash > 500 and customer_satisfaction < 50:
            lesson = {
                "day": day,
                "type": "cash_hoarding",
                "severity": "medium",
                "mistake": f"Hoarding ${cash:.0f} cash while satisfaction is {customer_satisfaction:.1f}%",
                "lesson": "Deploy capital! Use excess cash to increase inventory and capture more sales",
                "rule": "When cash > $500 and satisfaction < 70%, invest in larger inventory buffer"
            }
            new_lessons.append(lesson)
        
        # MISTAKE 4: Repeated same mistake (not learning)
        if len(new_lessons) > 0:
            for new_lesson in new_lessons:
                # Check if similar lesson exists in history
                similar_lessons = [
                    l for l in lessons_learned 
                    if l.get("type") == new_lesson["type"] and day - l.get("day", 0) <= 3
                ]
                if len(similar_lessons) >= 2:
                    new_lesson["severity"] = "critical"
                    new_lesson["lesson"] += " [REPEATED MISTAKE - NOT LEARNING!]"
                    logger.error(f"🚨 CRITICAL: AI repeating mistake type '{new_lesson['type']}'")
        
        # Add new lessons and keep last 10
        lessons_learned.extend(new_lessons)
        if len(lessons_learned) > 10:
            lessons_learned = lessons_learned[-10:]
        
        # Format lessons for AI display
        lessons_text = ""
        if lessons_learned:
            lessons_text = "⚠️ LESSONS FROM PAST MISTAKES:\n"
            for lesson in lessons_learned[-5:]:  # Show last 5 lessons
                severity_icon = "🚨" if lesson.get("severity") == "critical" else "⚠️" if lesson.get("severity") == "high" else "ℹ️"
                lessons_text += f"\n{severity_icon} Day {lesson.get('day')}: {lesson.get('mistake')}\n"
                lessons_text += f"   → LESSON: {lesson.get('lesson')}\n"
                lessons_text += f"   → RULE: {lesson.get('rule')}\n"
        else:
            lessons_text = "✅ No mistakes detected yet - keep up the good work!"
        
        # Create new state
        new_state = {
            "inventory": inventory,
            "cash": cash,
            "total_revenue": total_revenue,
            "machine_health": machine_health,
            "day": day + 1,
            "pending_orders": pending_orders if enable_delays else [],
            "net_worth": net_worth,
            "recent_decisions": recent_decisions,  # Raw data for analysis
            "decision_history_text": decision_history_text,  # Formatted for AI prompt
            "lessons_learned": lessons_learned,  # Raw lesson data
            "lessons_text": lessons_text  # Formatted for AI prompt
        }
        
        # Metrics (NEW: includes detailed costs + net worth)
        metrics = {
            "day": day,
            "customers": num_customers,
            "revenue": daily_revenue,
            "cost_of_goods": cost_of_goods_sold,
            "operating_costs": operating_costs,
            "restock_costs": restock_cost,
            "total_costs": total_daily_costs,
            "profit": daily_profit,
            "items_sold": sum(items_sold.values()),
            "stockouts": len(stockouts),
            "failed_purchases": failed_purchases,
            "malfunction_failures": malfunction_failures,  # NEW: Track machine health-related failures
            "customer_satisfaction": customer_satisfaction,
            "machine_health": machine_health,
            "cash_balance": cash,
            "inventory_value": inventory_value,
            "net_worth": net_worth,
        }
        
        # Events
        events = []
        
        if orders_arrived:
            events.append({
                "type": "order_arrived",
                "orders": orders_arrived,
                "severity": "info"
            })
        
        if stockouts:
            events.append({
                "type": "stockout",
                "items": stockouts,
                "severity": "high"
            })
        
        # NEW: Alert when machine malfunctions are significant
        if malfunction_failures > num_customers * 0.15:  # More than 15% failure rate
            events.append({
                "type": "machine_malfunctions",
                "malfunction_count": malfunction_failures,
                "machine_health": machine_health,
                "lost_revenue_estimate": round(malfunction_failures * 2.0, 2),  # Approx lost revenue
                "severity": "high" if malfunction_failures > num_customers * 0.25 else "medium"
            })
        
        if machine_health < 50:
            events.append({
                "type": "machine_failure",
                "health": machine_health,
                "severity": "critical"
            })
        
        if customer_satisfaction < 50:
            events.append({
                "type": "low_satisfaction",
                "satisfaction": customer_satisfaction,
                "severity": "medium"
            })
        
        # Bankruptcy detection with multiple severity levels
        if net_worth < 0:
            # CRITICAL: Net worth negative (debt exceeds assets)
            events.append({
                "type": "bankruptcy",
                "reason": "negative_net_worth",
                "cash": cash,
                "net_worth": net_worth,
                "severity": "critical"
            })
        elif cash < 0:
            # CRITICAL: Cash negative (can't pay bills)
            events.append({
                "type": "bankruptcy",
                "reason": "negative_cash",
                "cash": cash,
                "severity": "critical"
            })
        elif cash < operating_costs:
            # HIGH: Can't afford next day's operations
            events.append({
                "type": "insolvency_risk",
                "reason": "insufficient_cash_for_operations",
                "cash": cash,
                "required": operating_costs,
                "severity": "high"
            })
        
        logger.info(f"🏪 Day {day} simulated: ${daily_revenue:.2f} revenue, {num_customers} customers, satisfaction={customer_satisfaction:.0f}%")
        
        return {
            "new_state": new_state,
            "metrics": metrics,
            "events": events,
        }

