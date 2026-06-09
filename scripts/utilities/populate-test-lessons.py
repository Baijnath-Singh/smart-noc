#!/usr/bin/env python3
"""
Populate ChromaDB with test remediation lessons for Phase 2 testing
"""
import sys
sys.path.append('/vector_service')

from vector_service import VectorKnowledgeBase
import time

def populate_test_lessons():
    """Add test remediation lessons to ChromaDB"""
    
    print("Initializing Vector Knowledge Base...")
    vkb = VectorKnowledgeBase(
        chromadb_host='chromadb',
        chromadb_port=8000
    )
    
    # Test lessons with various incident types
    test_lessons = [
        {
            'id': 'test_bgp_1',
            'type': 'BGP_SESSION_DOWN',
            'device': 'core-router-01',
            'actions': 'clear_bgp_session, reload_bgp_config',
            'time': 15.3,
            'lesson': 'Successfully resolved BGP_SESSION_DOWN by clearing BGP session and reloading config. Resolution time: 15.3s',
            'success': True
        },
        {
            'id': 'test_interface_1',
            'type': 'INTERFACE_FLAPPING',
            'device': 'edge-switch-02',
            'actions': 'reload_interface, clear_interface_counters',
            'time': 12.5,
            'lesson': 'Successfully resolved INTERFACE_FLAPPING by reloading interface and clearing counters. Resolution time: 12.5s',
            'success': True
        },
        {
            'id': 'test_routing_1',
            'type': 'ROUTING_LOOP',
            'device': 'core-router-03',
            'actions': 'clear_routing_table, restart_ospf',
            'time': 22.1,
            'lesson': 'Successfully resolved ROUTING_LOOP by clearing routing table and restarting OSPF. Resolution time: 22.1s',
            'success': True
        },
        {
            'id': 'test_connectivity_1',
            'type': 'CONNECTIVITY_LOSS',
            'device': 'access-switch-01',
            'actions': 'reload_interface, check_cable',
            'time': 18.7,
            'lesson': 'Successfully resolved CONNECTIVITY_LOSS by reloading interface and checking physical cable. Resolution time: 18.7s',
            'success': True
        },
        {
            'id': 'test_unknown_1',
            'type': 'UNKNOWN',
            'device': 'core-router-01',
            'actions': 'clear_interface_counters, reload_interface',
            'time': 14.2,
            'lesson': 'Successfully resolved UNKNOWN by clearing interface counters and reloading interface. Resolution time: 14.2s',
            'success': True
        }
    ]
    
    print(f"\nAdding {len(test_lessons)} test remediation lessons to ChromaDB...")
    
    for lesson in test_lessons:
        # Build document text
        doc_text = f"""
Incident Type: {lesson['type']}
Device: {lesson['device']}
Actions: {lesson['actions']}
Resolution Time: {lesson['time']}s
Lesson: {lesson['lesson']}
""".strip()
        
        # Generate embedding
        embedding = vkb.model.encode(doc_text).tolist()
        
        # Store in remediation_commands collection
        vkb.commands.add(
            ids=[lesson['id']],
            embeddings=[embedding],
            metadatas=[{
                'incident_type': lesson['type'],
                'incident_number': lesson['id'].split('_')[-1],
                'device': lesson['device'],
                'success': lesson['success'],
                'resolution_time_seconds': lesson['time'],
                'actions_count': len(lesson['actions'].split(', ')),
                'stored_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }],
            documents=[doc_text]
        )
        
        print(f"  ✓ Added: {lesson['type']} on {lesson['device']}")
    
    # Verify
    stats = vkb.get_stats()
    print(f"\n✅ ChromaDB Stats:")
    print(f"   - Remediation Commands: {stats['commands']} documents")
    print(f"   - Knowledge Base: {stats['kb_articles']} documents")
    print(f"   - Incidents: {stats['incidents']} documents")
    
    print("\n🎉 Test data populated successfully!")
    print("\nYou can now test semantic search by generating a new incident.")

if __name__ == '__main__':
    populate_test_lessons()
