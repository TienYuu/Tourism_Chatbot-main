class EvidenceBuilder:
    def build_dynamic_evidence(self, paths):
        facts = []
        for path in paths:
            for rel in path.relationships:
                # Lấy tên nhãn thay vì mã P53 nếu có thể, hoặc giữ nguyên để LLM tự suy luận
                rel_type = rel.type.replace("P53_", "").replace("_", " ")
                start_label = rel.start_node.get('label', 'Unknown')
                end_label = rel.end_node.get('label', 'Unknown')
                
                facts.append(f"Fact: {start_label} có mối quan hệ '{rel_type}' với {end_label}")
                
                # Xử lý các thuộc tính dạng list (như instance_of, country trong debug của bạn)
                for node in [rel.start_node, rel.end_node]:
                    properties = []
                    for key, value in node.items():
                        if value:
                            # Nếu là list, nối lại thành chuỗi
                            val_str = ", ".join(value) if isinstance(value, list) else value
                            properties.append(f"{key}: {val_str}")
                    facts.append(f"Chi tiết về [{node.get('label')}]: {'; '.join(properties)}")
        
        return "\n".join(list(set(facts)))