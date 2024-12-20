import mongoose from "mongoose";

const promptSchema = new mongoose.Schema({
    title: {
        type:String,
        required:true,
    },
    prompt: {
        type:String,
        required:true,
    },
    userId:{
        type:String,
        required:true
    }
},{timestamps:true})

const Prompt = mongoose.model('Prompt', promptSchema)
export default Prompt