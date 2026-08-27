# MTG-Card-Winrate-Predictor
Overview

This project explores whether machine learning can predict a Magic: The Gathering card's Limited win rate based solely on its card text and attributes.

The project combines card data from Scryfall with historical Limited statistics from 17Lands. Scryfall provides information such as Oracle Text, mana cost, colors, and card type, while 17Lands provides observed performance metrics such as Games in Hand Win Rate (GIH WR). 

The model will learn relationships between a card's characteristics and its historical performance, with the goal of determining how much of a card's competitive value can be predicted from the card itself without using its historical win-rate data.

Implementation
Data: Scryfall card data + 17Lands Limited statistics
Input: Oracle Text and card attributes
Target: Historical 17Lands win-rate statistics
ML: Natural language processing, text embeddings, and regression models
Evaluation: Compare predicted win rates against observed 17Lands win rates using metrics such as MAE and $R^2$

The initial implementation will focus on a single Limited set to keep the scope manageable and control for differences between formats.