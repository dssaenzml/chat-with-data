import uuid
import pandas as pd
import json
from fastapi import UploadFile
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timedelta
import aiofiles
import chardet
from pathlib import Path

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class FileService:
    """Service for handling file uploads and data processing"""
    
    def __init__(self):
        self.upload_directory = Path(settings.upload_directory)
        self.upload_directory.mkdir(parents=True, exist_ok=True)
        self.processed_files: Dict[str, Dict[str, Any]] = {}
        
    async def process_uploaded_file(self, file: UploadFile) -> Dict[str, Any]:
        """Process uploaded file and return metadata"""
        try:
            # Generate unique file ID
            file_id = str(uuid.uuid4())
            
            # Validate file
            if not self._is_file_allowed(file.filename):
                raise ValueError(f"File type not allowed: {file.filename}")
            
            if file.size > settings.max_file_size:
                raise ValueError(f"File too large: {file.size} bytes")
            
            # Save file
            file_path = self.upload_directory / f"{file_id}_{file.filename}"
            
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            # Process file based on type
            file_type = self._get_file_type(file.filename)
            processing_result = await self._process_file_by_type(file_path, file_type)
            
            # Store metadata
            file_metadata = {
                "file_id": file_id,
                "filename": file.filename,
                "file_type": file_type,
                "file_path": str(file_path),
                "upload_time": datetime.utcnow(),
                "file_size": file.size,
                **processing_result
            }
            
            self.processed_files[file_id] = file_metadata
            
            logger.info(f"✅ File processed successfully: {file.filename}")
            
            return file_metadata
            
        except Exception as e:
            logger.error(f"❌ File processing failed: {e}")
            raise
    
    def _is_file_allowed(self, filename: str) -> bool:
        """Check if file type is allowed"""
        if not filename:
            return False
        
        file_extension = filename.split('.')[-1].lower()
        return file_extension in settings.allowed_file_types
    
    def _get_file_type(self, filename: str) -> str:
        """Get file type from filename"""
        return filename.split('.')[-1].lower()
    
    async def _process_file_by_type(self, file_path: Path, file_type: str) -> Dict[str, Any]:
        """Process file based on its type"""
        try:
            if file_type in ['csv']:
                return await self._process_csv(file_path)
            elif file_type in ['xlsx', 'xls']:
                return await self._process_excel(file_path)
            elif file_type == 'json':
                return await self._process_json(file_path)
            elif file_type == 'parquet':
                return await self._process_parquet(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
                
        except Exception as e:
            logger.error(f"❌ Failed to process {file_type} file: {e}")
            raise
    
    async def _process_csv(self, file_path: Path) -> Dict[str, Any]:
        """Process CSV file"""
        # Detect encoding
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            encoding = chardet.detect(raw_data)['encoding']
        
        # Read CSV
        df = pd.read_csv(file_path, encoding=encoding)
        
        return self._extract_dataframe_info(df)
    
    async def _process_excel(self, file_path: Path) -> Dict[str, Any]:
        """Process Excel file"""
        # Read first sheet
        df = pd.read_excel(file_path, sheet_name=0)
        
        # Get sheet names
        xl_file = pd.ExcelFile(file_path)
        sheet_names = xl_file.sheet_names
        
        result = self._extract_dataframe_info(df)
        result["sheet_names"] = sheet_names
        result["active_sheet"] = sheet_names[0] if sheet_names else None
        
        return result
    
    async def _process_json(self, file_path: Path) -> Dict[str, Any]:
        """Process JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert to DataFrame if possible
        if isinstance(data, list) and data and isinstance(data[0], dict):
            df = pd.DataFrame(data)
            return self._extract_dataframe_info(df)
        elif isinstance(data, dict):
            # Try to find a list of records
            for key, value in data.items():
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    df = pd.DataFrame(value)
                    result = self._extract_dataframe_info(df)
                    result["json_structure"] = key
                    return result
        
        # If not tabular data
        return {
            "rows": 1,
            "columns": len(data.keys()) if isinstance(data, dict) else 0,
            "preview": [data] if isinstance(data, dict) else data[:5] if isinstance(data, list) else [],
            "column_info": [],
            "data_types": {},
            "is_tabular": False
        }
    
    async def _process_parquet(self, file_path: Path) -> Dict[str, Any]:
        """Process Parquet file"""
        df = pd.read_parquet(file_path)
        return self._extract_dataframe_info(df)
    
    def _extract_dataframe_info(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract information from DataFrame"""
        # Basic info
        rows, columns = df.shape
        
        # Column information
        column_info = []
        data_types = {}
        
        for column in df.columns:
            col_type = str(df[column].dtype)
            null_count = df[column].isnull().sum()
            unique_count = df[column].nunique()
            
            column_info.append({
                "name": column,
                "type": col_type,
                "null_count": int(null_count),
                "unique_count": int(unique_count),
                "null_percentage": float(null_count / rows * 100) if rows > 0 else 0
            })
            
            data_types[column] = col_type
        
        # Preview data (first 5 rows)
        preview = df.head(5).to_dict('records')
        
        # Statistical summary for numeric columns
        numeric_summary = {}
        numeric_columns = df.select_dtypes(include=['number']).columns
        if len(numeric_columns) > 0:
            numeric_summary = df[numeric_columns].describe().to_dict()
        
        return {
            "rows": rows,
            "columns": columns,
            "preview": preview,
            "column_info": column_info,
            "data_types": data_types,
            "numeric_summary": numeric_summary,
            "is_tabular": True
        }
    
    async def load_sample_dataset(self, dataset_name: str) -> Dict[str, Any]:
        """Load a sample dataset"""
        try:
            # Sample datasets
            sample_datasets = {
                "Sales Data": self._generate_sales_data,
                "Customer Analytics": self._generate_customer_data,
                "Financial Reports": self._generate_financial_data,
                "E-commerce Transactions": self._generate_ecommerce_data
            }
            
            if dataset_name not in sample_datasets:
                raise ValueError(f"Unknown sample dataset: {dataset_name}")
            
            # Generate dataset
            df = sample_datasets[dataset_name]()
            
            # Generate file ID
            file_id = str(uuid.uuid4())
            
            # Save as CSV
            file_path = self.upload_directory / f"{file_id}_sample_{dataset_name.lower().replace(' ', '_')}.csv"
            df.to_csv(file_path, index=False)
            
            # Extract info
            file_info = self._extract_dataframe_info(df)
            file_info.update({
                "file_id": file_id,
                "filename": f"sample_{dataset_name.lower().replace(' ', '_')}.csv",
                "file_type": "csv",
                "file_path": str(file_path),
                "upload_time": datetime.utcnow(),
                "is_sample": True,
                "dataset_name": dataset_name
            })
            
            self.processed_files[file_id] = file_info
            
            logger.info(f"✅ Sample dataset loaded: {dataset_name}")
            
            return file_info
            
        except Exception as e:
            logger.error(f"❌ Failed to load sample dataset: {e}")
            raise
    
    def _generate_sales_data(self) -> pd.DataFrame:
        """Generate sample sales data"""
        import random
        
        base_date = datetime.now() - timedelta(days=365)
        
        data = []
        for i in range(1000):
            data.append({
                "order_id": f"ORD{1000 + i}",
                "customer_id": f"CUST{random.randint(1, 200)}",
                "product_name": random.choice(["Laptop", "Mouse", "Keyboard", "Monitor", "Headphones"]),
                "category": random.choice(["Electronics", "Accessories", "Computers"]),
                "quantity": random.randint(1, 5),
                "unit_price": round(random.uniform(10, 1000), 2),
                "total_amount": 0,  # Will calculate
                "order_date": base_date + timedelta(days=random.randint(0, 365)),
                "sales_rep": random.choice(["Alice", "Bob", "Charlie", "Diana", "Eve"]),
                "region": random.choice(["North", "South", "East", "West"])
            })
        
        df = pd.DataFrame(data)
        df["total_amount"] = df["quantity"] * df["unit_price"]
        
        return df
    
    def _generate_customer_data(self) -> pd.DataFrame:
        """Generate sample customer data"""
        import random
        
        data = []
        for i in range(500):
            data.append({
                "customer_id": f"CUST{i + 1}",
                "name": f"Customer {i + 1}",
                "email": f"customer{i + 1}@example.com",
                "age": random.randint(18, 80),
                "gender": random.choice(["Male", "Female", "Other"]),
                "city": random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"]),
                "signup_date": datetime.now() - timedelta(days=random.randint(1, 1000)),
                "total_orders": random.randint(0, 50),
                "total_spent": round(random.uniform(0, 5000), 2),
                "last_order_date": datetime.now() - timedelta(days=random.randint(1, 100)),
                "customer_segment": random.choice(["Premium", "Regular", "Basic"])
            })
        
        return pd.DataFrame(data)
    
    def _generate_financial_data(self) -> pd.DataFrame:
        """Generate sample financial data"""
        import random
        
        base_date = datetime.now() - timedelta(days=365)
        
        data = []
        for i in range(365):
            date = base_date + timedelta(days=i)
            data.append({
                "date": date,
                "revenue": round(random.uniform(10000, 50000), 2),
                "expenses": round(random.uniform(5000, 30000), 2),
                "profit": 0,  # Will calculate
                "department": random.choice(["Sales", "Marketing", "Operations", "HR"]),
                "budget_category": random.choice(["Fixed", "Variable", "Capital"]),
                "quarter": f"Q{((date.month - 1) // 3) + 1}",
                "year": date.year
            })
        
        df = pd.DataFrame(data)
        df["profit"] = df["revenue"] - df["expenses"]
        
        return df
    
    def _generate_ecommerce_data(self) -> pd.DataFrame:
        """Generate sample e-commerce data"""
        import random
        
        data = []
        for i in range(2000):
            data.append({
                "transaction_id": f"TXN{10000 + i}",
                "user_id": f"USER{random.randint(1, 500)}",
                "session_id": f"SESS{random.randint(1, 1000)}",
                "product_id": f"PROD{random.randint(1, 100)}",
                "product_category": random.choice(["Electronics", "Clothing", "Books", "Sports", "Home"]),
                "price": round(random.uniform(5, 500), 2),
                "quantity": random.randint(1, 3),
                "discount": round(random.uniform(0, 0.3), 2),
                "payment_method": random.choice(["Credit Card", "Debit Card", "PayPal", "Cash"]),
                "device_type": random.choice(["Desktop", "Mobile", "Tablet"]),
                "timestamp": datetime.now() - timedelta(hours=random.randint(1, 8760)),
                "is_returned": random.choice([True, False]) if random.random() < 0.1 else False
            })
        
        return pd.DataFrame(data)
    
    async def get_file_data(self, file_id: str) -> Optional[pd.DataFrame]:
        """Get DataFrame for a processed file"""
        try:
            if file_id not in self.processed_files:
                return None
            
            file_info = self.processed_files[file_id]
            file_path = Path(file_info["file_path"])
            
            if not file_path.exists():
                return None
            
            file_type = file_info["file_type"]
            
            if file_type == "csv":
                return pd.read_csv(file_path)
            elif file_type in ["xlsx", "xls"]:
                return pd.read_excel(file_path)
            elif file_type == "json":
                with open(file_path, 'r') as f:
                    data = json.load(f)
                return pd.DataFrame(data)
            elif file_type == "parquet":
                return pd.read_parquet(file_path)
                
        except Exception as e:
            logger.error(f"❌ Failed to load file data: {e}")
            return None
    
    async def delete_file(self, file_id: str) -> bool:
        """Delete a processed file"""
        try:
            if file_id not in self.processed_files:
                return False
            
            file_info = self.processed_files[file_id]
            file_path = Path(file_info["file_path"])
            
            if file_path.exists():
                file_path.unlink()
            
            del self.processed_files[file_id]
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete file: {e}")
            return False
    
    def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file information"""
        return self.processed_files.get(file_id)
