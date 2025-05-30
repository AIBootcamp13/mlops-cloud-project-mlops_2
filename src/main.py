import os
import sys
import fire
from dotenv import load_dotenv


sys.path.append(
    os.path.dirname( # /mlops/
        os.path.dirname(  # /mlops/src
            os.path.abspath(__file__)  # /mlops/src/main.py
        )
    )
)

from src.dataset.data_process import (
    read_dataset, apt_preprocess, train_val_split, 
    AptDataset, get_dataset
)
from src.utils.utils import init_seed
from src.model.model_cards import model_save, LGBMRegressorCard, CatBoostRegressorCard
from src.model.hyperparam_tuning import hyperparameter_tuning
from src.evaluate.evaluate import cross_validation
from src.inference.inference import load_checkpoint, load_model, get_inference_dataset, inference
from src.utils.constant import Models

init_seed()

def run_train(model_name, tuning_max_evals=None):
    # tuning_max_evals 옵션을 설정하면 하이퍼파라미터 튜닝을 진행, 
    # 설정하지 않으면 하이퍼파라미터 튜닝 없이 validation 진행.
    Models.validation(model_name)

    # if wandb add codes.

    # 데이터셋 및 DataLoader 생성
    apt = read_dataset('apt_trade_data.csv')
    # print(apt.shape)
    apt = apt_preprocess(apt)
    # print(apt.shape)
    apt, folds_idx = train_val_split(
        df=apt,
        datetime_col='datetime',
        n_folds=5,
        val_months=3
    )
    # print(len(folds_idx))
    fold_datasets = get_dataset(df=apt, folds_index=folds_idx)
    full_dataset = AptDataset(
        df=apt, scaler="No", encoders=dict()
    )

    # train and evaluate with folds
    model_card_class = Models[model_name.upper()].value
    model_card = model_card_class(
        early_stopping_rounds=50,
        random_seed=42
    )
    mean_val_score = float('inf')
    if tuning_max_evals is not None: # hyperparameter tuning
        model_card, mean_val_score = hyperparameter_tuning(
            model_card=model_card, fold_datasets=fold_datasets, max_evals=10
        )
    else: # hyperparameter tuning 안 함
        model_card, mean_val_score = cross_validation(model_card, fold_datasets)

    # full dataset으로 전체 학습
    # 현재 시점 model_card는 best_param으로 초기화되었고, 학습은 안 된 상태임.
    model_card.train(train_dataset=full_dataset, val_dataset=None)    
    ### model_save
    model_save(
        model_card=model_card,
        val_loss=mean_val_score,
        scaler=full_dataset.scaler,
        encoders=full_dataset.encoders,
    )

def run_inference(model_name, dataset=None):
    Models.validation(model_name)
    model_card_class = Models[model_name.upper()].value

    checkpoint_path = load_checkpoint(model_card_class.name)
    model, scaler, val_loss, encoders, early_stopping_rounds, random_seed = load_model(checkpoint_path)

    ### inference
    # init model card
    model_card = model_card_class(early_stopping_rounds, random_seed)
    model_card.model = model
    # get client request dataset : 사용자가 검색한 아파트 주소를 바탕으로 inference용 데이터셋 생성
    test_dataset = get_inference_dataset(scaler, encoders)
    # inference : 모델 추론
    result = inference(model_card, test_dataset)
    # send result to web.
    

if __name__ == '__main__':
    fire.Fire({
        "train": run_train,
        "inference": run_inference
    })

    # ### >>> run_train >>>

    # # 데이터셋 및 DataLoader 생성
    # apt = read_dataset('apt_trade_data.csv')
    # # print(apt.shape)
    # apt = apt_preprocess(apt)
    # # print(apt.shape)
    # apt, folds_idx = train_val_split(
    #     df=apt,
    #     datetime_col='datetime',
    #     n_folds=5,
    #     val_months=3
    # )
    # # print(len(folds_idx))
    # fold_datasets = get_dataset(df=apt, folds_index=folds_idx)
    # full_dataset = AptDataset(
    #     df=apt, scaler="No", encoders=dict()
    # )

    # # train and evaluate with folds
    # from tqdm import tqdm
    # model_card = CatBoostRegressorCard(
    #     early_stopping_rounds=50,
    #     random_seed=42
    # )
    # ### hyperparam tuning 여부
    # model_card, mean_val_score = hyperparameter_tuning(
    #     model_card=model_card, fold_datasets=fold_datasets, max_evals=10
    # )
    # print("hyperparameter tuned model card:",model_card.model)
    # print(mean_val_score)

    # ### hyperparam tuning 안 하는 경우 > evaluate.cross_validate
    # # model_card, mean_val_score = cross_validation(model_card, fold_datasets)

    # # full dataset으로 전체 학습
    # # 현재 시점 model_card는 best_param으로 초기화되었고, 학습은 안 된 상태임.
    # model_card.train(train_dataset=full_dataset, val_dataset=None)

    # ### model_save
    # model_save(
    #     model_card=model_card,
    #     val_loss=mean_val_score,
    #     scaler=full_dataset.scaler,
    #     encoders=full_dataset.encoders,
    # )
    # print('model saved')

    # ### <<< run_train <<<


    # ### >>> run_inference >>>

    # ### model_load 
    # checkpoint_path = load_checkpoint("CatBoostRegressor")
    # print("checkpoint:", checkpoint_path)
    # model, scaler, val_loss, encoders, early_stopping_rounds, random_seed = load_model(checkpoint_path)
    # print(model, val_loss)
    # print(scaler, encoders)

    # ### inference
    # # init model card
    # model_card = CatBoostRegressorCard(early_stopping_rounds, random_seed)
    # model_card.model = model
    # # get client request dataset : 사용자가 검색한 아파트 주소를 바탕으로 inference용 데이터셋 생성
    # test_dataset = get_inference_dataset(scaler, encoders)
    # # inference : 모델 추론
    # result = inference(model_card, test_dataset)
    # # send result to web.

    

    



