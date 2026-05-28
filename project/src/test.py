import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Tải cấu hình từ file .env [2]
load_dotenv(override=True)
URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE")

def debug_heritage_entity(entity_name):
    # Khởi tạo Driver kết nối Neo4j [3]
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    
    # Query 1: Kiểm tra xem Node có tồn tại không và các thuộc tính của nó là gì
    # Sử dụng Regex (?i) để không phân biệt hoa thường [2]
    query_node = """
    MATCH (n) 
    WHERE n.label =~ $regex OR n.name =~ $regex
    RETURN n, labels(n) as node_labels
    LIMIT 5
    """
    
    # Query 2: Kiểm tra các quan hệ (Relationships) xung quanh Node đó
    query_rel = """
    MATCH (n)-[r]-(m)
    WHERE n.label =~ $regex OR n.name =~ $regex
    RETURN n.label as source, type(r) as rel_type, m.label as target
    LIMIT 10
    """
    
    regex = f"(?i).*{entity_name}.*"
    
    try:
        with driver.session(database=DATABASE) as session:
            print(f"=== ĐANG KIỂM TRA THỰC THỂ: '{entity_name}' ===")
            
            # --- KIỂM TRA NODE ---
            nodes = session.run(query_node, regex=regex)
            found_any = False
            for record in nodes:
                found_any = True
                node = record["n"]
                print(f"\n[1. ĐÃ TÌM THẤY NODE]")
                print(f"- Labels: {record['node_labels']}")
                print(f"- Toàn bộ thuộc tính (Properties): {dict(node)}")
                
                # Kiểm tra tương thích với EvidenceBuilder [1]
                label = node.get('label')
                if not label:
                    print("⚠️ CẢNH BÁO: Node không có thuộc tính 'label'. EvidenceBuilder sẽ không hiển thị được tên!")

            if not found_any:
                print(f"\n❌ LỖI: Không tìm thấy bất kỳ Node nào có 'label' hoặc 'name' chứa '{entity_name}'")
                print("Lời khuyên: Kiểm tra lại dữ liệu trong Neo4j Browser bằng lệnh: MATCH (n) RETURN n LIMIT 10")

            # --- KIỂM TRA QUAN HỆ ---
            print(f"\n[2. CÁC MỐI QUAN HỆ (RELATIONSHIPS)]")
            rels = session.run(query_rel, regex=regex)
            rel_found = False
            for record in rels:
                rel_found = True
                print(f"   {record['source']} --[{record['rel_type']}]--> {record['target']}")
            
            if not rel_found:
                print("⚠️ CẢNH BÁO: Node này đang bị 'cô lập' (không có quan hệ). Multi-hop reasoning sẽ không hoạt động.")

    except Exception as e:
        print(f"❌ LỖI KẾT NỐI: {str(e)}")
    finally:
        driver.close()

if __name__ == "__main__":
    # Thử nghiệm trực tiếp với 'Huế'
    debug_heritage_entity("Huế")