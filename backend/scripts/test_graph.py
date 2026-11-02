import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from langchain_core.messages import HumanMessage
from app.agents.graph import nexus_graph

async def test():
    config = {'configurable': {'thread_id': 'test-session-1'}}
    initial_state = {
        'messages': [HumanMessage(content='Write a python function add(a, b) with docstring and a test.')],
        'generated_code': {},
        'review_feedback': '',
        'iterations': 0,
        'current_node': 'init'
    }
    print("Testing astream on nexus_graph...")
    step_count = 0
    async for output in nexus_graph.astream(initial_state, config=config):
        step_count += 1
        for node_name, node_state in output.items():
            files = list(node_state.get('generated_code', {}).keys())
            feedback_preview = str(node_state.get('review_feedback', ''))[:80]
            print(f"Step {step_count}: Node '{node_name}' finished. Files: {files}. Feedback: {feedback_preview}")

    print("Workflow finished successfully!")

if __name__ == '__main__':
    asyncio.run(test())
