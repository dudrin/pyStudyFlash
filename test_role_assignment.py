#!/usr/bin/env python3
"""
Test script to debug role assignment logic
"""

import time
import uuid

def test_role_assignment():
    print("=== Testing Role Assignment Logic ===")
    
    # Simulate server role assignment logic
    clients = {}
    controller_id = None
    
    def register_client(client_id, display_name, current_controller_id):
        print(f"\n[DEBUG] register_client called - client_id: '{client_id}', display_name: '{display_name}'")
        print(f"[DEBUG] Before registration - current clients: {len(clients)}, controller: {current_controller_id}")
        
        if not client_id:
            print(f"[DEBUG] Empty client_id, returning")
            return current_controller_id
            
        display_name = display_name or client_id
        
        # Check existing client
        existing_info = clients.get(client_id)
        is_new_client = existing_info is None
        is_reconnection = existing_info is not None
        
        print(f"[DEBUG] Client analysis - is_new: {is_new_client}, is_reconnection: {is_reconnection}")
        
        if is_new_client:
            # New client
            info = {
                'name': display_name,
                'status': 'Connected',
                'connected_at': time.time(),
                'role': 'viewer',  # Default role
                'connection_count': 1
            }
            clients[client_id] = info
            print(f'📥 NEW CLIENT: {display_name} ({client_id})')
            
        else:
            # Reconnection
            existing_info['name'] = display_name
            existing_info['status'] = 'Connected'
            existing_info['connected_at'] = time.time()
            existing_info['connection_count'] = existing_info.get('connection_count', 0) + 1
            print(f'🔄 RECONNECTION: {display_name} ({client_id}) - attempt #{existing_info["connection_count"]}')
            
        # Role assignment
        print(f"[DEBUG] Before role assignment - controller: {current_controller_id}, total clients: {len(clients)}")
        new_controller_id = assign_roles_for_multiple_clients(clients, current_controller_id)
        print(f"[DEBUG] After role assignment - controller: {new_controller_id}")
        
        # Show final roles
        print(f"[DEBUG] Final client roles:")
        for cid, info in clients.items():
            role = info.get('role', 'unknown')
            print(f"[DEBUG]   {cid} -> {role.upper()}")
        
        return new_controller_id
    
    def assign_roles_for_multiple_clients(clients, controller_id):
        print(f"[DEBUG] assign_roles_for_multiple_clients called")
        print(f"[DEBUG] Current state - clients: {len(clients)}, controller_id: {controller_id}")
        
        if not clients:
            print(f"[DEBUG] No clients, setting controller_id to None")
            return None
            
        # If no valid controller or it disconnected
        if not controller_id or controller_id not in clients:
            print(f"[DEBUG] No valid controller, finding earliest client")
            # Find earliest client by connection time
            earliest_client = min(
                clients.items(), 
                key=lambda item: item[1].get('connected_at', 0)
            )
            
            old_controller = controller_id
            controller_id = earliest_client[0]
            
            print(f'[DEBUG] 👑 CONTROLLER ASSIGNMENT: {earliest_client[1].get("name", earliest_client[0])} (first connected)')
            print(f'[DEBUG] Controller changed from {old_controller} to {controller_id}')
        else:
            print(f"[DEBUG] Controller {controller_id} is still valid")
                
        # Set roles for all clients
        print(f"[DEBUG] Setting roles for all clients:")
        for client_id, info in clients.items():
            old_role = info.get('role', 'unknown')
            if client_id == controller_id:
                info['role'] = 'controller'
                print(f"[DEBUG]   {client_id} -> CONTROLLER (was {old_role})")
            else:
                info['role'] = 'viewer'
                print(f"[DEBUG]   {client_id} -> VIEWER (was {old_role})")
                
        return controller_id
    
    # Test scenarios
    print("\n=== Test 1: First Client Connection ===")
    client1_id = str(uuid.uuid4())[:8]
    controller_id = register_client(client1_id, "DESKTOP-CLIENT1", controller_id)
    
    expected_controller = client1_id
    actual_controller = controller_id
    client1_role = clients[client1_id]['role']
    
    print(f"\nExpected controller: {expected_controller}")
    print(f"Actual controller: {actual_controller}")
    print(f"Client1 role: {client1_role}")
    print(f"✅ PASS" if client1_role == 'controller' and controller_id == client1_id else "❌ FAIL")
    
    print("\n=== Test 2: Second Client Connection ===")
    time.sleep(0.1)  # Small delay to ensure different connection time
    client2_id = str(uuid.uuid4())[:8]
    controller_id = register_client(client2_id, "DESKTOP-CLIENT2", controller_id)
    
    client2_role = clients[client2_id]['role']
    print(f"\nClient1 role: {clients[client1_id]['role']}")
    print(f"Client2 role: {client2_role}")
    print(f"Controller: {controller_id}")
    print(f"✅ PASS" if clients[client1_id]['role'] == 'controller' and client2_role == 'viewer' else "❌ FAIL")

if __name__ == "__main__":
    test_role_assignment()