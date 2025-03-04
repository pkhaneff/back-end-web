import Chatbot from "../models/chatbot.model.js"
import Prompt from "../models/prompt.model.js"
import { errorHandler } from "../utils/error.js"

export const importdata = async (req, res, next) => {
    if(!req.user.isAdmin){
        return next(errorHandler(403, 'You are not allowed to import data'))
    }
    if(!req.body.title) {
        return next(errorHandler(400, 'Please provide all required fields'))
    }
    const newData = new Chatbot({
        ...req.body, userId: req.user.id
    })
    try {
        const saveData = await newData.save()
        res.status(201).json(saveData)
    } catch (error) {
        next(error)
    }
}

export const = async (req, res, next) => {
    if(!req.user.isAdmin) return next(errorHandler(403,'You are not allowed to get all data chatbot'))
    try {
        const chatbots = await Chatbot.find();

        if (!chatbots chatbots.length === 0) {
            return res.status(404).json({ message: 'No chatbots found' });
        }

        return res.status(200).json(chatbots);
    } catch (error) {
        console.error(error);
        next(error)
    }
};

export const customPrompt = async (req, res, next) => {
    if(!req.user.isAdmin){
        return next(errorHandler(403, 'You are not allowed to import data'))
    }
    if(!req.body.title || !req.body.prompt) {
        return next(errorHandler(400, 'Please provide all required fields'))
    }
    const newPrompt = new Prompt({
        ...req.body, userId: req.user.id
    })
    try {
        const savePrompt = await newPrompt.save()
        res.status(201).json(savePrompt)
    } catch (error) {
        next(error)
    }
}


export const getprompt = async (req, res, next) => {
    if(!req.user.isAdmin) return next(errorHandler(403,'You are not allowed to get all data chatbot'))
    try {
        const prompts = await Prompt.find();

        if (!prompts || prompts.length === 0) {
            return res.status(404).json({ message: 'No prompt found' });
        }

        return res.status(200).json(prompts);
    } catch (error) {
        console.error(error);
        next(error)
    }
};