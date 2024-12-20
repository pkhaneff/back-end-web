import mongoose from "mongoose";

const chatbotSchema = new mongoose.Schema({
    title: {
        type:String,
        required:true,
    },
    file: {
        type:String,
        required:true,
    },
    userId:{
        type:String,
        required:true
    }
},{timestamps:true})

const Chatbot = mongoose.model('Chatbot', chatbotSchema)
export default Chatbot