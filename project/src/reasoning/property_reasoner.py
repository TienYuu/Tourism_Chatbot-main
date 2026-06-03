class PropertyReasoner:

    def __init__(self, graph_query):
        self.graph_query = graph_query

    # =====================================================
    # PROPERTY QUESTION ANSWERING
    # =====================================================

    def answer_property_question(self, entity_id, semantic_parse):
        relations = semantic_parse.get("relations", [])

        if not relations:
            return None

        relation = str(relations[0]).lower().strip()

        node = self.graph_query.get_entity_by_id(entity_id)

        if not node:
            return None

        # =================================================
        # COORDINATES (TỌA ĐỘ)
        # =================================================
        coordinate_keywords = [
            "kinh độ", "vĩ độ", "tọa độ", 
            "coordinates", "latitude", "longitude"
        ]

        if any(keyword in relation for keyword in coordinate_keywords):
            latitude = node.get("latitude")
            longitude = node.get("longitude")

            if latitude is not None and longitude is not None:
                return {
                    "answer": f"Vĩ độ: {latitude}, Kinh độ: {longitude}",
                    "latitude": latitude,
                    "longitude": longitude
                }

        # =================================================
        # ADDRESS (ĐỊA CHỈ)
        # =================================================
        address_keywords = [
            "địa chỉ", "address", "ở số mấy", "đường nào", 
            "vị trí cụ thể", "địa chỉ cụ thể"
        ]

        if any(keyword in relation for keyword in address_keywords):
            # Tìm trong node thuộc tính 'address' hoặc 'location_address' tùy cấu trúc DB của bạn
            address = node.get("address") or node.get("location_address")
            if address:
                return {
                    "answer": str(address).strip(),
                    "property": "address"
                }

        # =================================================
        # DESCRIPTION (MÔ TẢ / THÔNG TIN CHUNG)
        # =================================================
        description_keywords = [
            "mô tả", "description", "giới thiệu", "là gì", 
            "thông tin về", "tóm tắt", "sơ lược"
        ]

        if any(keyword in relation for keyword in description_keywords):
            # Thường DB lưu là 'description', 'summary', hoặc 'comment' (theo chuẩn Wikidata/Wikibase)
            description = node.get("description") or node.get("summary") or node.get("comment")
            if description:
                return {
                    "answer": str(description).strip(),
                    "property": "description"
                }

        # =================================================
        # COUNTRY (QUỐC GIA)
        # =================================================
        country_keywords = [
            "quốc gia", "nước nào", "thuộc nước", "quốc tịch", 
            "country", "citizen of"
        ]

        if any(keyword in relation for keyword in country_keywords):
            # Tìm giá trị quốc gia trực tiếp từ thuộc tính của node
            country = node.get("country") or node.get("nation")
            if country:
                return {
                    "answer": str(country).strip(),
                    "property": "country"
                }

        return None