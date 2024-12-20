import express from 'express'
import { verifyToken } from '../utils/verifyUser.js'
import {importdata, getdata, customPrompt, getprompt} from "../controllers/chatbot.controller.js"

const router = express.Router()

router.post('/import-data',verifyToken, importdata)
router.get('/data',verifyToken, getdata)
router.post('/custom-prompt', verifyToken, customPrompt)
router.get('/prompt',verifyToken, getprompt)

export default router