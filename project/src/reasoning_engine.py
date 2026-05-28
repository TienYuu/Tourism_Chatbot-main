import re
import json
from graph_query import HeritageGraphQuery
from groq_client import extract_question_entities
from utils import safe_json_load 

class HeritageReasoner:
    def __init__(self, graph, builder):
        self.graph = graph
        self.builder = builder

    def reason(self, question):
        # Gọi trực tiếp hàm, không dùng self.client
        raw_output = extract_question_entities(question) 
        
        # CHỖ CẦN SỬA: Chuyển chuỗi thành dictionary
        try:
            parsed = json.loads(raw_output) 
        except:
            # Sử dụng hàm safe_json_load của bạn để xử lý các ký tự thừa
            parsed = safe_json_load(raw_output) 

        # Bây giờ parsed đã là dict, lệnh get() sẽ hoạt động
        entities = parsed.get("entities", [])
        
        all_context = ""
        for entity in entities:
            # 2. Truy vấn vùng đồ thị xung quanh thực thể (Dynamic Multi-hop)
            paths = self.graph.get_subgraph_context(entity, hops=2)
            # 3. Chuyển đổi thành văn bản facts
            all_context += self.builder.build_dynamic_evidence(paths) + "\n"
            
        return all_context