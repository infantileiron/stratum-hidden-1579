from pydantic import BaseModel,Field,ConfigDict
from typing import Literal
class InputModel(BaseModel):
 model_config=ConfigDict(allow_inf_nan=False)
class LoginInput(InputModel):
 email:str
 password:str
class DatasetInput(InputModel):
 name:str=Field(min_length=2,max_length=100)
 source:str=Field(default='shenxi_logs_202611.csv',max_length=100)
 csv_text:str=Field(min_length=10,max_length=400000)
class RenameDataset(InputModel):
 name:str=Field(min_length=2,max_length=100)
class StateModelInput(InputModel):
 name:str=Field(min_length=2,max_length=100)
 model_json:str=Field(min_length=2,max_length=15000)
class SequenceStudyInput(InputModel):
 name:str=Field(min_length=2,max_length=100)
 dataset_id:str
 model_id:str
 borehole:str=Field(min_length=1,max_length=30)
class RunInput(InputModel):
 study_id:str
class ReviewInput(InputModel):
 run_id:str
 comment:str=Field(min_length=5,max_length=2000)
class DecisionInput(InputModel):
 status:Literal['approved','rejected']
 comment:str=Field(min_length=5,max_length=2000)
class ReportInput(InputModel):
 run_id:str
 review_id:str
 title:str=Field(min_length=2,max_length=100)
class MappingEntry(InputModel):
 state:str=Field(min_length=1,max_length=20)
 category:str=Field(min_length=1,max_length=30)
class ComparisonMapping(InputModel):
 categories:list[str]=Field(min_length=1,max_length=8)
 run_a:list[MappingEntry]=Field(min_length=2,max_length=4)
 run_b:list[MappingEntry]=Field(min_length=2,max_length=4)
class ComparisonInput(InputModel):
 run_a_id:str
 run_b_id:str
 mapping:ComparisonMapping
class RemapInput(InputModel):
 mapping:ComparisonMapping
