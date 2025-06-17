# roles_config.py - 角色配置管理器喵~

import json
import os
from typing import Dict, List, Optional
from datetime import datetime

class RolesManager:
    """
    角色管理器类，负责加载、保存和管理预设角色
    """
    
    def __init__(self, data_file: str = "roles_data.json"):
        self.data_file = os.path.join(os.path.dirname(__file__), data_file)
        self._roles_data = {}
        self.load_roles()
    
    def load_roles(self) -> bool:
        """
        从JSON文件加载角色数据
        """
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self._roles_data = json.load(f)
                print(f"✅ Loaded {len(self.get_all_roles())} roles from {self.data_file}")
                return True
            else:
                print(f"⚠️  Roles data file not found: {self.data_file}")
                self._create_default_data()
                return False
        except Exception as e:
            print(f"❌ Error loading roles data: {e}")
            self._create_default_data()
            return False
    
    def save_roles(self) -> bool:
        """
        保存角色数据到JSON文件
        """
        try:
            # 更新元数据
            if "metadata" not in self._roles_data:
                self._roles_data["metadata"] = {}
            
            self._roles_data["metadata"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
            self._roles_data["metadata"]["total_roles"] = len(self.get_all_roles())
            
            # 保存到文件
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self._roles_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Roles data saved to {self.data_file}")
            return True
        except Exception as e:
            print(f"❌ Error saving roles data: {e}")
            return False
    
    def _create_default_data(self):
        """
        创建默认的角色数据结构
        """
        self._roles_data = {
            "predefined_roles": {},
            "metadata": {
                "version": "1.0",
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
                "total_roles": 0,
                "categories": []
            }
        }
    
    def get_role_description(self, role_name: str) -> str:
        """
        获取角色描述，支持大小写不敏感查找
        """
        roles = self._roles_data.get("predefined_roles", {})
        
        # 首先尝试精确匹配
        if role_name in roles:
            return roles[role_name]
        
        # 然后尝试不区分大小写匹配
        for key, value in roles.items():
            if key.lower() == role_name.lower():
                return value
        
        return ""
    
    def get_all_roles(self) -> Dict[str, str]:
        """
        获取所有预设角色
        """
        return self._roles_data.get("predefined_roles", {})
    
    def list_role_names(self) -> List[str]:
        """
        列出所有角色名称
        """
        return list(self.get_all_roles().keys())
    
    def add_role(self, role_name: str, description: str, save_immediately: bool = True) -> bool:
        """
        添加新角色
        """
        try:
            if "predefined_roles" not in self._roles_data:
                self._roles_data["predefined_roles"] = {}
            
            self._roles_data["predefined_roles"][role_name] = description
            
            if save_immediately:
                return self.save_roles()
            return True
        except Exception as e:
            print(f"❌ Error adding role '{role_name}': {e}")
            return False
    
    def remove_role(self, role_name: str, save_immediately: bool = True) -> bool:
        """
        移除角色
        """
        try:
            roles = self._roles_data.get("predefined_roles", {})
            if role_name in roles:
                del roles[role_name]
                if save_immediately:
                    return self.save_roles()
                return True
            return False
        except Exception as e:
            print(f"❌ Error removing role '{role_name}': {e}")
            return False
    
    def update_role(self, role_name: str, description: str, save_immediately: bool = True) -> bool:
        """
        更新角色描述
        """
        return self.add_role(role_name, description, save_immediately)
    
    def search_roles(self, keyword: str) -> Dict[str, str]:
        """
        搜索包含关键词的角色
        """
        result = {}
        keyword_lower = keyword.lower()
        
        for name, desc in self.get_all_roles().items():
            if (keyword_lower in name.lower() or 
                keyword_lower in desc.lower()):
                result[name] = desc
        
        return result
    
    def get_metadata(self) -> Dict:
        """
        获取元数据信息
        """
        return self._roles_data.get("metadata", {})

# 创建全局实例
roles_manager = RolesManager()

# 提供便捷的函数接口（向后兼容）
def get_role_description(role_name: str) -> str:
    return roles_manager.get_role_description(role_name)

def list_available_roles() -> List[str]:
    return roles_manager.list_role_names()

def add_role(role_name: str, description: str) -> bool:
    return roles_manager.add_role(role_name, description)

def remove_role(role_name: str) -> bool:
    return roles_manager.remove_role(role_name)

def save_roles() -> bool:
    return roles_manager.save_roles()

def reload_roles() -> bool:
    return roles_manager.load_roles()